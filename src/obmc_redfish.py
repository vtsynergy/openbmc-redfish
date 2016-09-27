#! /usr/bin/python

#Author : Anshuman Verma (anshuman@vt.edu) 
#Date	: Aug 26th, 2016 
#Description : 
#Implements redifsh APIs using bottle for Board Management Controller using 
#Dbus interface for querying, and performing tasks. 
#This code must comly to pep8 and redfish standards 
#Redfish uses HTTP operations including GET, PUT, PATCH, POST, DELETE and HEAD.
#GET retrieves data.  POST is used for creating resources or to use actions.
#DELETE will delete a resource, but there are currently only a few resources 
#that can be deleted.  PATCH is used to change one or more 
#properties on a resource , while PUT is used to replace a resource entirely 
#(though only a few resources can be completely replaced).  HEAD is similar to
#GET without the body data returned , and can be used for figuring out the URI 
#structure by programs accessing a Redfish implementation.

import json
import sys 
import dbus
#from bottle import route, run, template, get, post


REDFISH_VERSION = str("1.0.2")
REDFISH_PATH = "/redfish/v1"
REDFISH_COPY_RIGHTS = ("Copyright 2014-2016 Distributed Management "
                      "Task Force, Inc. (DMTF). For the full DMTF "
                      "copyright policy, see "
                      "http://www.dmtf.org/about/policies/copyright.")
R_OD_ID = "@odata.id"

POWER_CONTROL = { 'on'         : 'powerOn'
                 ,'off'        : 'powerOff' 
                 ,'soft_off'   : 'softPowerOff'
                 ,'reboot'     : 'reboot'
                 ,'soft_reboot': 'softReboot' 
                 ,'state'      : 'getPowerState'
                 }


SENSORS_INFO = {
                'AMBIENT'         : 'ambient' 
               ,'BOOT_PROGRESS'   : 'BootProgress' 
               ,'SYSTEM_POWER'    : 'system_power' 
               ,'OCC_STATUS'      : 'OccStatus' 
               ,'CURR_POWER_CAP'  : 'curr_cap'
               ,'OP_SYS_STAT'     : 'OperatingSystemStatus' 
               ,'POWER_CAP'       : 'PowerCap' 
               ,'POWER_MIN_CAP'   : 'min_cap' 
               ,'POWER_MAX_CAP'   : 'max_cap' 
               ,'POWER_NORMAL_CAP': 'n_cap' 
               ,'POWER_USER_CAP'  : 'user_cap'
               ,'BOOT_COUNT'      : 'BootCount' 
               }

## System states
##   state can change to next state in 2 ways:
##   - a process emits a GotoSystemState signal with state name to goto
##   - objects specified in EXIT_STATE_DEPEND have started
SYSTEM_STATES = [
	'BASE_APPS',
	'BMC_STARTING',
	'BMC_READY',
	'HOST_POWERING_ON',
	'HOST_POWERED_ON',
	'HOST_BOOTING',
	'HOST_BOOTED',
	'HOST_POWERED_OFF',
]

INVENTORY_ITEMS = [ 
         'SYSTEM'
        ,'MAIN_PLANAR'
        ,'FAN'
        ,'BMC'
        ,'CPU'
        ,'CORE'
        ,'DIMM'
        ,'PCIE_CARD'
        ,'SYSTEM_EVENT'
        ,'MEMORY_BUFFER'
]


v1 = {   "@odata.type"    : "#ServiceRoot.v1_0_2.ServiceRoot" 
        ,"Id"             : "RootService"
        ,"Name"           : "Root Service" 
        ,"RedfishVersion" : REDFISH_VERSION
        ,"UUID"           : "blank" 
        ,"Systems"        : {R_OD_ID : REDFISH_PATH+"/Systems"}
        ,"Chassis"        : {R_OD_ID : REDFISH_PATH+"/Chassis"}
        ,"Managers"       : {R_OD_ID : REDFISH_PATH+"/Managers"}
        ,"Tasks"          : {R_OD_ID : REDFISH_PATH+"/AccountService"}
        ,"EventService"   : {R_OD_ID : REDFISH_PATH+"/EventService"}
        ,"Links"          : {"Sessions":
                            {R_OD_ID : REDFISH_PATH+"/SessionService/Sessions"}}
        ,"Oem"            : ""
        ,"@odata.context" : REDFISH_PATH+"/$metadata#ServiceRoot"
        ,R_OD_ID          : REDFISH_PATH
        ,"@Redfish.Copyright" : REDFISH_COPY_RIGHTS
        }


systems = {  "@odata.type" : 
                "#ComputerSystemCollection.ComputerSysteamCollection"
            ,"Name"                : "Computer System Collection" 
            ,"Members@odata.count" : "1"
            ,"members"             : [
                {R_OD_ID : REDFISH_PATH+"/Systems/FixIt"}
                ]
            ,R_OD_ID              : REDFISH_PATH+"/Systems"
            ,"@Redfish.Copyright" : REDFISH_COPY_RIGHTS
          }


#@get('/redfish')
#def getV1():
#    return json.dumps({"v1" : "/redfish/v1"})
#
#
#@get('/redfish/v1')
#def getAllInfo():
#    if "UUID" in v1.keys():
#        v1["UUID"] = getSystemId()
#    else :
#        print "UUID not found"
#    return json.dumps(v1)
#
#@get('/redfish/v1/Systems')
#def getSystems(): 
#    return json.dumps(systems)
#
#
#run(host='localhost', port=8080)

	       

def fixByte(it,key,parent):   
    if (isinstance(it,dbus.Array)):
        for i in range(0,len(it)): 
            fixByte(it[i],i,it)
    elif (isinstance(it, dict)):   
        for key in it.keys():      
            fixByte(it[key],key,it)
    elif (isinstance(it,dbus.Byte)):   
        if (key != None):              
            parent[key] = int(it)  
    elif (isinstance(it,dbus.Double)):
        if (key != None):
            parent[key] = float(it)
    else:                              
        pass                           

def flattenDict(object):
    for op in object: 
	merged = {}
	for property,value in object[op].items():
	    merged.update(value)
	del object[op]
	object[op] = merged 


def findInventoryObject(name,object): 
    merged = {} 
    for op in object: 
        for property,value in object[op].items(): 
            if value['fru_type'] == name: 
                merged[op] = value
    return merged;

def findSensorValue(name,object):
    merged = {} 
    for op in object: 
        p_op = op.split('/')
	if p_op[-1] == name:
	   for prop, value in object[op].items(): 
		 merged.update(value)
    return merged;


def printDict(name,data):
    	if (isinstance(data, dict)):   
	    print ">>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>"
	    print name
	    for p in sorted(data.keys()):
                printDict(p,data[p])
	else:
	    print name+" = "+str(data)


def getInventory(name): 
    obj = bus.get_object('org.openbmc.Inventory',
            '/org/openbmc/inventory') 
    intf = dbus.Interface(obj,'org.freedesktop.DBus.ObjectManager')
    mthd = obj.get_dbus_method("GetManagedObjects",
            'org.freedesktop.DBus.ObjectManager')
    try:
        data = mthd()
        fixByte(data,None,None)
	pydata = json.loads(json.dumps(data))
	inventory_object = findInventoryObject(name, pydata)
    except Exception as e:
        print e 
    return inventory_object;


def getSensors(sensor):
    sensor_values = {} 
    sensor_values['type'] = sensor
    obj = bus.get_object('org.openbmc.Sensors',
            '/org/openbmc/sensors') 
    intf = dbus.Interface(obj,'org.freedesktop.DBus.ObjectManager')
    mthd = obj.get_dbus_method("GetManagedObjects",
            'org.freedesktop.DBus.ObjectManager')
    try:
        data = mthd()
        fixByte(data,None,None)
	pydata = json.loads(json.dumps(data))
	s_value = findSensorValue(SENSORS_INFO[sensor], pydata)
        for item, values in s_value.items():
	       if (item == 'value' or 
		   item == 'units' or 
	           item == 'filename' or 
		   item == 'error'):
                    sensor_values[item] = values
    except Exception as e:
        print e 
    
    sensor_values['value'] = str(sensor_values['value']) + sensor_values['units']
    del sensor_values['units']
    return sensor_values;


def getSystemState(): 
    obj = bus.get_object('org.openbmc.managers.System'
                        ,'/org/openbmc/managers/System')
    intf = dbus.Interface(obj,'org.openbmc.managers.System')
    mthd = obj.get_dbus_method('getSystemState',
                         'org.openbmc.managers.System')
    try:
        data = mthd() 
        fixByte(data,None,None)
        pydata = json.loads(json.dumps(data))
        print pydata
    except Exception as e: 
        print e 

#getSystemState()

def getCpuInfo(): 
    info = {} 
    item = getInventory('CPU')
    for cpu,info in item.items(): 
        for key,value in info.items(): 
            if key == 'Manufacturer' : 
                info['Manufacturer'] = value 

    print info

def getCpuCoreCount():
    cores = [] 
    item = getInventory('CORE') 
    for core,info in item.items():
        for key,value in info.items():
            if key == 'present' and value == 'True': 
                cores.append('core')
    return len(cores)

def getChassisInfo(): 
    info = {} 
    item = getInventory('MEMORY_BUFFER')
    for chassis, detail in item.items():
        for key, value in detail.items(): 
            if key == 'Custom Field 1': 
                info['Id'] = str(value)
            elif key == 'Manufacturer':
                info['Manufacturer'] = str(value)
            elif key == 'Name' :
                info['Model'] = str(value) 
            elif key == 'Part Number': 
                info['PartNumber'] = str(value)
            elif key == 'Serial Number':
                info['SerialNumber'] = str(value)
    return info

def powerControl(name): 
    if name in POWER_CONTROL.keys():
        method_name = POWER_CONTROL[name] 
        obj = bus.get_object('org.openbmc.control.Chassis'
                        ,'/org/openbmc/control/chassis0')
        intf = dbus.Interface(obj,'org.openbmc.control.Chassis')
        mthd = obj.get_dbus_method(method_name,
                         'org.openbmc.control.Chassis')
        out = mthd()
        return out;
    else: 
        print "Command %s not found" % name

def getSystemId():
    obj = bus.get_object('org.openbmc.control.Chassis',
            '/org/openbmc/control/chassis0')
    intf = dbus.Interface(obj,"org.freedesktop.DBus.Properties")
    props = intf.GetAll('org.openbmc.control.Chassis') 
    intf = dbus.Interface(obj,'org.freedesktop.DBus.ObjectManager')
    data = intf.GetManagedObjects()
    #mthd = obj.get_dbus_method("GetManagedObjects",
    #                           'org.freedesktop.DBus.ObjectManager')
    #data = mthd() 
    fixByte(data,None,None)
    pydata = json.loads(json.dumps(data))
    print pydata
    for p in props: 
        if p == 'uuid': 
            return str(props[p])

def getLedState():
    obj = bus.get_object('org.openbmc.control.led',
                         '/org/openbmc/control/led/identify')
    intf = dbus.Interface(obj,'org.openbmc.Led')
    data = intf.GetLedState();
    fixByte(data,None,None)
    pydata = json.loads(json.dumps(data))
    print pydata

#Not working yet
def getHostSettings(): 
    obj = bus.get_object('org.openbmc.settings.Host',
                         '/org/openbmc/settings/host0')
    intf = dbus.Interface(obj,'org.freedesktop.Dbus.Properties')
    data = intf.GetAll('org.openbmc.settings.Host')
    fixByte(data,None,None)
    pydata = json.loads(json.dumps(data))
    print pydata

def setMaxFanSpeed():
    obj = bus.get_object('org.openbmc.control.Fans',
                         '/org/openbmc/control/fans')
    intf = dbus.Interface(obj,'org.openbmc.control.Fans')
    data = intf.setMax()
    #fixByte(data,None,None)
    #pydata = json.loads(json.dumps(data))
    #print pydata


def getFanSpeed():
    obj = bus.get_object('org.openbmc.control.Fans',
                         '/org/openbmc/control/fans')
    intf = dbus.Interface(obj,"org.freedesktop.DBus.Properties")
    data = intf.GetAll('org.openbmc.control.Fans') 
    fixByte(data,None,None)
    pydata = json.loads(json.dumps(data))
    print pydata


bus = dbus.SystemBus()

print getSystemId()
print powerControl('state')
print getLedState()
getSystemState()
#getHostSettings()
getFanSpeed()
print 'Number of cores: %d'  % getCpuCoreCount()
print getChassisInfo()

#for inventory_item in INVENTORY_ITEMS:
#    item = getInventory(inventory_item)
#    print ">>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>"
#    #print item 
#    printDict("",item)
#
#for sensors in SENSORS_INFO.keys():
#    value = getSensors(sensors) 
#    printDict("",value) 
#


#getInventory()
#getSensors()

