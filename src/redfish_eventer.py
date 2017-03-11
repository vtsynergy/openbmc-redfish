#! /usr/bin/env python

# Description : Eventer for OpenBMC Redfish

import json
import urllib2
import time
import Queue
import threading
import datetime
import os

"""
Redfish Eventing Persistent Static Storage File Path
"""
TMP_MEM_PATH = '/var/tmp/'
TMP_MEM_FILENAME = 'subscriptions.json'

SUBSCRIPTIONS_FP = os.path.join(TMP_MEM_PATH, TMP_MEM_FILENAME)

"""
Redfish Eventing Enumerations
"""
EVENT_TYPES = {'STATUS_CHANGE': 'StatusChange',
               'RESOURCE_UPDATED': 'ResourceUpdated',
               'RESOURCE_ADDED': 'ResourceAdded',
               'RESOURCE_REMOVED': 'ResourceRemoved',
               'ALERT': 'Alert'}

EVENT_PROPS = {'ID': 'Id',
               'NAME': 'Name',
               'EVENTS': 'Events',
               'CONTEXT': 'Context'}

EVENT_RECORD_PROPS = {'EVENT_TYPE': 'EventType',
                      'MESSAGE_ID': 'MessageId',
                      'EVENT_RECORD_ID': 'EventId',
                      'EVENT_TIMESTAMP': 'EventTimestamp'}


class EventRecord(object):
    """EventRecord respresents the changes that occurred for an event"""

    def __init__(self, event_type, message_id):
        self.attrs = {}
        self.attrs[EVENT_RECORD_PROPS['EVENT_TYPE']] = event_type
        self.attrs[EVENT_RECORD_PROPS['MESSAGE_ID']] = message_id
        # TODO add event UUID
        self.attrs[EVENT_RECORD_PROPS['EVENT_RECORD_ID']] = ''
        ts = time.time()
        st = datetime.datetime.fromtimestamp(ts).strftime('%Y-%m-%d %H:%M:%S')
        self.attrs[EVENT_RECORD_PROPS['EVENT_TIMESTAMP']] = st


class Event(object):
    """
    Event represents the message sent to a subscribed client which includes
    a list of EventRecord objects
    """

    def __init__(self, event_destination_id, name, context):
        self.attrs = {}
        self.attrs[EVENT_PROPS['ID']] = event_destination_id
        self.attrs[EVENT_PROPS['NAME']] = name
        self.attrs[EVENT_PROPS['CONTEXT']] = context

    def set_event_records(self, event_records):
        """
        extracts the event_record attributes, attrs, for serializing to JSON
        """
        self.attrs[EVENT_PROPS['EVENTS']] = event_records


class EventerJSONEncoder(json.JSONEncoder):
    def default(self, o):
        if isinstance(o, Event) or isinstance(o, EventRecord):
            return o.attrs
        print 'fail'
        return o.__dict__


class Eventer(object):
    """
    Eventer Handles Emitting Life Cycle and Alert Events to Subscribed Clients
    """

    def __init__(self, service_enabled, delivery_retry_attempts,
                 delivery_retry_interval_seconds):
        self.service_enabled = service_enabled
        self.delivery_retry_attempts = delivery_retry_attempts
        self.delivery_retry_interval_seconds = delivery_retry_interval_seconds
        self.client_URI_endpoints = self.read_subscriptions_from_tmp()

    def create_subscription(self, client_URI_endpoint, event_destination_id,
                            name, subscription_context):
        """
        Adds the client_URI_endpoint to dict of subscribed clients and writes
        the subscribed client list to persistent memory
        """
        self.client_URI_endpoints[client_URI_endpoint] = \
            Event(event_destination_id, name, subscription_context)
        self.write_subscriptions_to_tmp(self.client_URI_endpoints)

    def remove_subscription(self, url):
        """
        Removes the url from the subscribed client dict and ensures that the
        EventDestinationCollection resource with that url is removed as well.
        Writes these changes to persistent memory
        """
        deleted_resource_id = self.client_URI_endpoints.pop(url)
        # TODO del subscription resource from EventDestinationCollection resrc
        # TODO implement remove resource method for CollectionResources
        self.write_subscriptions_to_tmp(self.client_URI_endpoints)

    def byteify(self, input):
        """Encodes the openned subscriptions json file into utf-8 strings"""
        if isinstance(input, dict):
            return {self.byteify(key): self.byteify(value)
                    for key, value in input.iteritems()}
        elif isinstance(input, list):
            return [self.byteify(element) for element in input]
        elif isinstance(input, unicode):
            return input.encode('utf-8')
        else:
            return input

    def read_subscriptions_from_tmp(self):
        """
        returns dictionary of the subscriptions json file to persistent memory
        """
        if os.path.isfile(SUBSCRIPTIONS_FP) \
                and os.stat(SUBSCRIPTIONS_FP).st_size > 0:
            with open(SUBSCRIPTIONS_FP, 'r') as data_file:
                c_objs = self.byteify(json.load(data_file))
                for c in c_objs:
                    c_objs[c] = Event(c_objs[c][EVENT_PROPS['ID']],
                                      c_objs[c][EVENT_PROPS['NAME']],
                                      c_objs[c][EVENT_PROPS['CONTEXT']])
                return c_objs
        return {}

    def write_subscriptions_to_tmp(self, subscriptions):
        """Writes the subscriptions dictionary to persistent memory"""
        with open(SUBSCRIPTIONS_FP, 'w') as data_file:
            json.dump(subscriptions, data_file, cls=EventerJSONEncoder)

    def publish_event(self, event_records):
        """POSTs the dictionary, body, to all subscribed clients"""
        if self.service_enabled is False:
            return

        running_threads = []
        result_queue = Queue.Queue()
        for client_URI_endpoint in self.client_URI_endpoints.keys():
            event = self.client_URI_endpoints[client_URI_endpoint]
            event.set_event_records(event_records)

            thr = threading.Thread(
                target=self.post_to_client,
                args=(
                    client_URI_endpoint,
                    event.attrs,
                    result_queue
                )
            )
            thr.start()
            running_threads.append(thr)

        for running_thread in running_threads:
            running_thread.join()

        while not result_queue.empty():
            failed_client_url = result_queue.get()
            self.remove_subscription(failed_client_url)

    def post_to_client(self, url, body, result_queue):
        """
        POSTs the payload, body, to the url of the client and records failures
        in threadsafe result_queue
        """
        data = json.dumps(body, cls=EventerJSONEncoder)
        req = urllib2.Request(url, data)
        req.add_header('Content-Type', 'application/json')
        for _ in xrange(self.delivery_retry_attempts):
            try:
                connection = urllib2.urlopen(req)
                if connection.code == 200:
                    response = connection.read()
                    connection.close()
                    return True
            except urllib2.HTTPError, err:
                print 'server error occurred'
                print err
            time.sleep(self.delivery_retry_interval_seconds)
        print url, 'client endpoint did not respond'
        result_queue.put(url)
        return False
