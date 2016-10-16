#! /usr/bin/env python

import json
import sys 
from bottle import Bottle, route, run, template, get, post
from redfish_resource import *

app = Bottle() 

redfish_root = RedfishBottleRoot()

@app.get('/<path:path>') 
def print_path(path):
    """provide the path to redfish build tree and get a response"""
    path_list = path.split('/')
    return redfish_root.get_json(path_list)

@app.post('/<path:path>')
def post_action(path):
    path_list = path.split('/')
    return redfisn_root.do_action(path_list,request)

app.run(host='localhost', port=8080, debug=True)
