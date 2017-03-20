#! /usr/bin/env python

import sys
import os
import logging
from bottle import Bottle, abort, request, response, JSONPlugin, HTTPError
from redfish_resource import *
from rocket import Rocket


class RouteHandler(object):

    def __init__(self, app, verbs, rules, redfish):
        self.app = app
        self.redfish = redfish
        self._verbs = verbs
        self._rules = rules

    def _setup(self, **kw):
        request.route_data = {}
        if request.method in self._verbs:
            return self.setup(**kw)
        else:
            self.find(**kw)
            raise HTTPError(
                405, "Method not allowed.", Allow=','.join(self._verbs))

    def __call__(self, **kw):
        return getattr(self, 'do_' + request.method.lower())(**kw)

    def install(self):
        self.app.route(
            self._rules, callback=self,
            method=['GET', 'PUT', 'PATCH', 'POST', 'DELETE'])

    def is_error(self, packet):
        data = json.loads(packet)
        if "error" in data.keys():
            return True 
        else:
            return False


class GetRequestHandler(RouteHandler):
    verbs = ['GET', 'POST']
    rules = '/<path:path>'

    def __init__(self, app, redfish):
        super(GetRequestHandler, self).__init__(
            app, self.verbs, self.rules, redfish)

    def find(self, path='/'):
        """provide the path to redfish build tree and get a response"""
        path_list = path.split('/')
        server_data = self.redfish.get_json(path_list)
        if self.is_error(server_data) is True:
            raise HTTPError(404, server_data)
        else:
            return server_data
        

    def setup(self, path='/'):
        request.route_data['map'] = self.find(path)

    def do_get(self, path='/'):
        return self.find(path)

    def find_post(self, path='/'):
        """provide the path to redfish build tree and get a response"""
        path_list = path.split('/')
        return self.redfish.do_action(path_list, request)

    def do_post(self, path):
        return self.find_post(path)


class RedfishServer(Bottle):

    def __init__(self, root):
        super(RedfishServer, self).__init__(autojson=False)
        self.redfish_root = root
        self.create_handlers()
        self.install_handlers()

    def create_handlers(self):
        self.get_request_handler = GetRequestHandler(self, self.redfish_root)

    def install_handlers(self):
        self.get_request_handler.install()


if __name__ == '__main__':
    log = logging.getLogger('Rocket.Errors')
    log.setLevel(logging.INFO)
    log.addHandler(logging.StreamHandler(sys.stdout))
    redfish_root = RedfishBottleRoot()

    app = RedfishServer(redfish_root)
    default_cert = os.path.join(
        sys.prefix, 'share', os.path.basename(__file__), 'cert.pem')

    server = Rocket(
        ('0.0.0.0', 8080, default_cert, default_cert),
        'wsgi', {'wsgi_app': app},
        min_threads=1,
        max_threads=1)
    print "Starting Server"
    server.start()
