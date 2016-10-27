#! /usr/bin/env python

import json
import sys
from redfish_resource import *

"""Temporary module to check the functionality on OpenBMC without running
Bottle. Does not belong to final release of the modules"""


redfish_root = RedfishBottleRoot()

get_paths = ['redfish',
             'redfish/v1',
             'redfish/v1/Systems',
             'redfish/v1/Systems/0000000000000000',
             'redfish/v1/Systems/0000000000000000/Processors',
             'redfish/v1/Systems/0000000000000000/Processors/CPU0',
             'redfish/v1/Systems/0000000000000000/Memory',
             'redfish/v1/Systems/0000000000000000/Memory/DIMM0',
             'redfish/v1/Systems/0000000000000000/Memory/DIMM1',
             'redfish/v1/Systems/0000000000000000/Memory/DIMM2',
             'redfish/v1/Systems/0000000000000000/Memory/DIMM3',
             'redfish/v1/Chassis',
             'redfish/v1/Chassis/1U']

for path in get_paths:
    path_list = path.split('/')
    print "-----------------------------"
    print path
    print "-----------------------------"
    jdata = redfish_root.get_json(path_list)
    print json.dumps(json.loads(jdata), sort_keys=True,
                     indent=4, separators=(',', ': '))
