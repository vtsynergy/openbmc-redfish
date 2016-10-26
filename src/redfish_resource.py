#! /usr/bin/env python

# Author: Anshuman Verma
# Date  : Oct 5, 2016
# Description : Resource for Redfish

import sys
import json
from obmc_redfish_providers import *

"""
Redfish Resource Types
"""

REDFISH_VERSION = str("1.0.3")
REDFISH_COPY_RIGHT = ("Copyright 2014-2016 Distributed Management "
                      "Task Force, Inc. (DMTF). For the full DMTF "
                      "copyright policy, see "
                      "http://www.dmtf.org/about/policies/copyright.")

ODATA_ID = "@odata.id"
ODATA_TYPE = "@odata.type"
ODATA_CONTEXT = "@odata.context"


class RedfishBase(object):
    """Base class for Redfish Obejcts"""

    def __init__(self, name):

        self.attrs = {}
        """Dictionary of redfish attributes"""

        self.child = []
        """List of children resources"""

        self.actions = {}
        """Dictonary for action, key=Function, value = List of allowable
        values"""

        self.related_object = []
        """List of related objects"""

        self.name = name
        """name for the class that specifies the Path to resource"""

        self.static_data_filled = 0
        """Flag to show if the static data was filled in attrs dictonary, update
        the flag when the static data is filled, would be updated when the
        resource is queried for the first time"""

        self.attrs["@Redfish.Copyright"] = REDFISH_COPY_RIGHT

        self.metadata_path = "/redfish/v1/$metadata"
        """Hardcoded the above, need to get it updated when adding metadata
        functionality"""

    def add_child(self, obj):
        """Add a child to the node"""
        self.child.append(obj)
        obj.path = str(self.path + "/" + obj.name)
        obj.parent = self
        obj.attrs[ODATA_ID] = obj.path
        obj.provider = self.provider

    def print_attr(self):
        """debug function for printing values"""
        for key in self.attrs.keys():
            print key + " : " + str(self.attrs[key])
        print self.name
        print "Path : %s" % getattr(self, "path")

    def print_all(self):
        """Print all attribute for tree"""
        print "----------------------------------------"
        self.print_attr()
        print "----------------------------------------"
        for children in self.child:
            children.print_all()

    def fill_static_data(self):
        """Fill the static attributes of attrs dictonary at build. Extend this
        function in inherited classes to update the information"""
        pass

    def fill_dynamic_data(self):
        """Update or fill the attributes of attrs dictonary when a get request
        is recieved. Extend in inherited classes"""
        pass

    def add_related_object(self, obj):
        """Add a related object to this item"""
        self.related_object.append(obj)

    def get_export_data(self, op):
        """Export the json data to server"""
        """FIXME: this with correct functions calls in case of error"""
        if op[0] != self.name or len(op) == 0:
            print "Error:" + self.name + str(len(op)) + str(op[0])
            return "Error: Last name did not match" + self.name
        elif len(op) > 1:
            for children in self.child:
                if children.name == op[1]:
                    op.pop(0)
                    return children.get_export_data(op)
            else:
                return "Error: Child does not exist"
        else:
            if self.static_data_filled == 0:
                self.fill_static_data()
                self.static_data_filled = 1
            self.fill_dynamic_data()
            print "Returning" + str(op)
            return json.dumps(self.attrs)

    def action(self, path, op):
        """Perfrom the requested action and return the information"""
        """FIXME: Fill in the details for Error Class"""
        if path[0] != self.name or len(path) == 1:
            print "[ACTION] Error: " + self.name + str(len(op)) + str(op[0])
        elif len(path) > 3:
            for children in self.child:
                if children.name == path[1]:
                    path.pop(0)
                    return children.action(path, op)
            else:
                return "Error [ACTION]: Path not correct"
        else:
            if path[1] != 'Action':
                return "Error: Action URI is incorrect"
            else:
                action_list = path[2].split('.')
                uri_namespace = action_list[0]
                action = action_list[1]
                if action in self.actions.keys():
                    print "FIXME: get attribute"
                else:
                    print "FIXME: return error object,  action is undefined"
                print uri_namespace + action + str(op.POST.items())
                return

    def add_action(self, act, op):
        if(isinstance(op, list)):
            self.actions[act] = op
        else:
            print "Error: Pass a list"

    def fancy_uuid(self, op):
        op = op.upper()
        while len(op) < 32:
            op = "0" + op
        res = (op[0:8] + "-" + op[8:12] + "-" + op[12:16] + "-" + op[16:20] +
               "-" + op[20:32])
        return res


class RedfishCollectionBase(RedfishBase):
    """Base class for Redfish Collections"""

    def __init__(self, name):
        super(RedfishCollectionBase, self).__init__(name)
        self.attrs["Members@odata.count"] = 0

    def add_child(self, obj):
        super(RedfishCollectionBase, self).add_child(obj)
        self.attrs["Members@odata.count"] += 1

    def fill_static_data(self):
        super(RedfishCollectionBase,self).fill_static_data()
        self.attrs["Members"] = []
        for children in self.child:
            self.attrs["Members"].append(dict([(ODATA_ID, children.path)]))


class RedfishRoot(RedfishBase):
    """Root object for redfish, located at 'redfish'"""

    def __init__(self, name, provider):
        super(RedfishRoot, self).__init__(name)
        self.path = str("/" + name)
        self.provider = provider

    def add_child(self, ob):
        """When adding child for root, delete all the attributes"""
        super(RedfishRoot, self).add_child(ob)
        for key in self.attrs.keys():
            del self.attrs[key]
        self.attrs[ob.name] = ob.path


class ServiceRoot(RedfishBase):
    """Root Manager for Redfish"""

    def __init__(self, name, instance_id):
        super(ServiceRoot, self).__init__(name)
        self.namespace = "ServiceRoot"
        """Namespace for ServiceRoot"""

        self.instance_id = instance_id
        """Section: 7.6.1 Id for the resourse. Shall be unique """

        self.version = "v1_0_3.ServiceRoot"
        """Schema Version"""

        self.instance_name = "Root Service"
        """Section: 7.6.2 Human Readable Name, Need not be Unique"""

        self.metadata_path = self.metadata_path + "#" + self.namespace


    def fill_static_data(self):
        super(ServiceRoot, self).fill_static_data()

        self.attrs["Id"] = self.instance_id
        self.attrs["Name"] = self.instance_name
        self.attrs["RedfishVersion"] = REDFISH_VERSION
        self.attrs[ODATA_TYPE] = "#" + self.namespace + "." + self.version
        for children in self.child:
            self.attrs[children.name] = dict([(ODATA_ID, children.path)])
        uuid = self.provider.get_system_id()
        self.attrs["UUID"] = self.fancy_uuid(uuid)
        self.attrs[ODATA_CONTEXT] = self.metadata_path

class SystemCollection(RedfishCollectionBase):
    """Computer System Collection class"""

    def __init__(self, name, instance_id):
        super(SystemCollection, self).__init__(name)
        self.instance_id = instance_id
        self.namespace = "ComputerSystemCollection"
        self.version = "ComputerSystemCollection"
        self.metadata_path = self.metadata_path + "#" + self.name

    def fill_static_data(self):
        super(SystemCollection, self).fill_static_data()
        self.attrs["Name"] = self.instance_id
        self.attrs[ODATA_TYPE] = "#" + self.namespace + "." + self.version
        self.attrs[ODATA_CONTEXT] = self.metadata_path


class ChassisCollection(RedfishCollectionBase):
    """Chassis Collection"""

    def __init__(self, name, instance_id):
        super(ChassisCollection, self).__init__(name)
        self.instance_id = instance_id
        self.namespace = "ChassisCollection"
        self.version = "ChassisCollection"
        self.metadata_path = self.metadata_path + "#" + self.name

    def fill_static_data(self):
        super(ChassisCollection, self).fill_static_data()
        self.attrs["Name"] = self.instance_id
        self.attrs[ODATA_TYPE] = "#" + self.namespace + "." + self.version
        self.attrs[ODATA_CONTEXT] = self.metadata_path

class ChassisInstance(RedfishBase):
    """Chassis Information"""

    def __init__(self, name):
        super(ChassisInstance, self).__init__(name)


class System(RedfishBase):
    """System Information"""

    def __init__(self, name, argv):
        super(System, self).__init__(name)
        self.namespace = "ComputerSystem"
        self.version = "v1_0_3.ComputerSystem"
        for keys in argv.keys():
            if keys is "UUID":
                uuid = argv[keys].split(':')
                self.attrs[keys] = self.fancy_uuid(uuid[1])
            else:
                self.attrs[keys] = argv[keys].strip()

    def fill_static_data(self):
        super(System, self).fill_static_data()
        self.attrs[ODATA_TYPE] = "#" + self.namespace + "." + self.version
        self.metadata_path = self.parent.metadata_path + "/Members/$entity" 
        self.attrs[ODATA_CONTEXT] = self.metadata_path
        self.attrs["Id"] = self.name

    def fill_dynamic_data(self):
        super(System, self).fill_dynamic_data()
        print self.provider.get_led_state()


class CpuInstance(RedfishBase):
    """CPU Information"""

    def __init__(self, name):
        super(CpuInstance, self).__init__(name)


class RedfishBottleRoot(object):
    """Class that contains and builds the resource tree"""

    def __init__(self):
        """Build the resource tree in a top-down fashion"""
        self.provider = ObmcRedfishProviders()

        self.root = RedfishRoot("redfish", self.provider)

        self.v1 = ServiceRoot("v1", "RootService")
        self.root.add_child(self.v1)

        self.chassis_collection = ChassisCollection("Chassis",
                                           "Chassis Collection")
        self.v1.add_child(self.chassis_collection)

        self.system_collection = SystemCollection("Systems",
                                                  "Computer System Collection")
        self.v1.add_child(self.system_collection)

        self.chassis_info = self.provider.get_chassis_info()
        
        print str(self.chassis_info)

        self.system = System(self.chassis_info['SerialNumber'], 
                             self.chassis_info)

        self.system_collection.add_child(self.system)


    def print_all(self):
        self.root.print_all()

    def get_json(self, path):
        return self.root.get_export_data(path)

    def do_action(self, path, obj):
        return self.root.action(path, obj)
