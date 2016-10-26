#! /usr/bin/env python

import json
import sys
from redfish_resource import *

"""Temporary module to check the functionality on OpenBMC without running
Bottle. Does not belong to final release of the modules"""


redfish_root = RedfishBottleRoot()

get_paths = ['redfish',
             'redfish/v1']



for path in get_paths:
    path_list = path.split('/')
    print "-----------------------------"
    print path
    print "-----------------------------"
    print redfish_root.get_json(path_list)
