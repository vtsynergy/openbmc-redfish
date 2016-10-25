#! /usr/bin/env python

import json
import sys
from redfish_resource import *


redfish_root = RedfishBottleRoot()

get_paths = ['redfish',
             'redfish/v1']



for path in get_paths:
    path_list = path.split('/')
    print redfish_root.get_json(path_list)
