#! /usr/bin/env python

import json
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


class GetRequestHandler(RouteHandler):
    verbs = 'GET'
    rules = '/<path:path>'

    def __init__(self, app, redfish):
        super(GetRequestHandler, self).__init__(
            app, self.verbs, self.rules, redfish)

    def find(self, path='/'):
        """provide the path to redfish build tree and get a response"""
        path_list = path.split('/')
        print path_list
        return self.redfish.get_json(path_list)

    def setup(self, path='/'):
        request.route_data['map'] = self.find(path)

    def do_get(self, path='/'):
        return self.find(path)


class RedfishServer(Bottle):

    def __init__(self):
        super(RedfishServer, self).__init__(autojson=False)
        self.redfish_root = RedfishBottleRoot()
        self.create_handlers()
        self.install_handlers()

    def create_handlers(self):
        self.get_request_handler = GetRequestHandler(self, self.redfish_root)

    def install_handlers(self):
        self.get_request_handler.install()

    def custom_router_match(self, environ):
        ''' The built-in Bottle algorithm for figuring out if a 404 or 405 is
            needed doesn't work for us since the instance rules match
            everything. This monkey-patch lets the route handler figure
            out which response is needed.  This could be accomplished
            with a hook but that would require calling the router match
            function twice.
        '''
        route, args = self.real_router_match(environ)
        if isinstance(route.callback, RouteHandler):
            route.callback._setup(**args)

        return route, args

#    @post('/<path:path>')
#    def post_action(path):
#        path_list = path.split('/')
#        return self.redfish_root.do_action(path_list, request)


if __name__ == '__main__':
    log = logging.getLogger('Rocket.Errors')
    log.setLevel(logging.INFO)
    log.addHandler(logging.StreamHandler(sys.stdout))

    app = RedfishServer()
    default_cert = os.path.join(
        sys.prefix, 'share', os.path.basename(__file__), 'cert.pem')

    server = Rocket(
        ('0.0.0.0', 8080, default_cert, default_cert),
        'wsgi', {'wsgi_app': app},
        min_threads=1,
        max_threads=1)
    print "Starting Server"
    server.start()
