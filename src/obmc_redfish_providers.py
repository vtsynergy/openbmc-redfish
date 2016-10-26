#! /usr/bin/env python

# Author:  Anshuman Verma (anshuman@vt.edu)
# Date   :  Aug 26th, 2016
# Description:
# Implements redifsh APIs using bottle for Board Management Controller using
# Dbus interface for querying, and performing tasks.
# This code must comly to pep8 and redfish standards
# Redfish uses HTTP operations including GET, PUT, PATCH, POST, DELETE, HEAD.
# GET retrieves data.  POST is used for creating resources or to use actions.
# DELETE will delete a resource, but there are currently only a few resources
# that can be deleted.  PATCH is used to change one or more
# properties on a resource, while PUT is used to replace a resource entirely
# (though only a few resources can be completely replaced).  HEAD is similar to
# GET without the body data returned, and can be used for figuring out the URI
# structure by programs accessing a Redfish implementation.

import json
import sys
import dbus
# from bottle import route, run, template, get, post


POWER_CONTROL = {'On': 'powerOn',
                 'ForceOff': 'powerOff',
                 'GracefulShutDown': 'softPowerOff',
                 'ForceRestart': 'reboot',
                 'GracefulRestart': 'softReboot',
                 'state': 'getPowerState'
                 }


SENSORS_INFO = {
               'AMBIENT': 'ambient',
               'BOOT_PROGRESS': 'BootProgress',
               'SYSTEM_POWER': 'system_power',
               'OCC_STATUS': 'OccStatus',
               'CURR_POWER_CAP': 'curr_cap',
               'OP_SYS_STAT': 'OperatingSystemStatus',
               'POWER_CAP': 'PowerCap',
               'POWER_MIN_CAP': 'min_cap',
               'POWER_MAX_CAP': 'max_cap',
               'POWER_NORMAL_CAP':  'n_cap',
               'POWER_USER_CAP': 'user_cap',
               'BOOT_COUNT': 'BootCount'}

# System states
#   state can change to next state in 2 ways:
#   - a process emits a GotoSystemState signal with state name to goto
#   - objects specified in EXIT_STATE_DEPEND have started
SYSTEM_STATES = {
        'BASE_APPS': "Off",
        'BMC_STARTING': "Off",
        'BMC_READY': "Off",
        'HOST_POWERING_ON': "PoweringOn",
        'HOST_POWERED_ON': "PoweringOn",
        'HOST_BOOTING': "PoweringOn",
        'HOST_BOOTED': "On",
        'HOST_POWERED_OFF': "Off"}

LED_FUNCTIONS = {'On': 'setOn',
                 'Off': 'setOff',
                 'BlinkFast': 'setBlinkFast',
                 'BlinkSlow': 'setBlinkSlow',
                 'state': 'GetLedState'}

LED_TYPE = ['identify', 'power', 'heartbeat']

INVENTORY_ITEMS = [
        'SYSTEM',
        'MAIN_PLANAR',
        'FAN',
        'BMC',
        'CPU',
        'CORE',
        'DIMM',
        'PCIE_CARD',
        'SYSTEM_EVENT',
        'MEMORY_BUFFER'
]


class ObmcRedfishProviders(object):
    """OpenBMC Redfish Providers using DBUS"""

    def __init__(self):
        """Initialize the class"""
        self.bus = dbus.SystemBus()

    def fix_byte(self, it, key, parent):
        if (isinstance(it, dbus.Array)):
            for i in range(0, len(it)):
                self.fix_byte(it[i], i, it)
        elif (isinstance(it, dict)):
            for key in it.keys():
                self.fix_byte(it[key], key, it)
        elif (isinstance(it, dbus.Byte)):
            if key is not None:
                parent[key] = int(it)
        elif (isinstance(it, dbus.Double)):
            if key is not None:
                parent[key] = float(it)
        else:
            pass

    def flatten_dict(self, object):
        merged = {}
        for op in object:
            for property, value in object[op].items():
                merged.update(value)
        del object[op]
        object[op] = merged

    def find_inventory_object(self, name, object):
        merged = {}
        for op in object:
            for property, value in object[op].items():
                if value['fru_type'] == name:
                    merged[op] = value
        return merged

    def get_system_count(self):
        return 2

    def find_sensor_value(self, name, object):
        merged = {}
        for op in object:
            p_op = op.split('/')
        if p_op[-1] == name:
            for prop, value in object[op].items():
                merged.update(value)
        return merged

    def print_dict(self, name, data):
        if (isinstance(data, dict)):
            print ">>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>"
            print name
            for p in sorted(data.keys()):
                    self.print_dict(p, data[p])
        else:
            print name+" = "+str(data)

    def get_inventory(self, name):
        obj = self.bus.get_object('org.openbmc.Inventory',
                                  '/org/openbmc/inventory')
        intf = dbus.Interface(obj, 'org.freedesktop.DBus.ObjectManager')
        mthd = obj.get_dbus_method("GetManagedObjects",
                                   'org.freedesktop.DBus.ObjectManager')
        try:
            data = mthd()
            self.fix_byte(data, None, None)
            pydata = json.loads(json.dumps(data))
            inventory_object = self.find_inventory_object(name, pydata)
        except Exception as e:
            print e
        return inventory_object

    def get_sensors(self, sensor):
        sensor_values = {}
        sensor_values['type'] = sensor
        obj = self.bus.get_object('org.openbmc.Sensors',
                                  '/org/openbmc/sensors')
        intf = dbus.Interface(obj, 'org.freedesktop.DBus.ObjectManager')
        mthd = obj.get_dbus_method("GetManagedObjects",
                                   'org.freedesktop.DBus.ObjectManager')
        try:
            data = mthd()
            self.fix_byte(data, None, None)
            pydata = json.loads(json.dumps(data))
            s_value = self.find_sensor_value(SENSORS_INFO[sensor], pydata)
            for item, values in s_value.items():
                if(item == 'value' or
                   item == 'units' or
                   item == 'filename' or
                   item == 'error'):
                    sensor_values[item] = values
        except Exception as e:
            print e
# FIXME: 'value' not found
# sensor_values['value'] = str(sensor_values['value']) + sensor_values['units']
# del sensor_values['units']
        return sensor_values

    def get_system_type(self):
        """Refer to the Redfish Specification for available types"""
        return "Physical"

    def get_system_state(self):
        obj = self.bus.get_object('org.openbmc.managers.System',
                                  '/org/openbmc/managers/System')
        intf = dbus.Interface(obj, 'org.openbmc.managers.System')
        mthd = obj.get_dbus_method('getSystemState',
                                   'org.openbmc.managers.System')
        try:
            data = mthd()
            self.fix_byte(data, None, None)
            pydata = json.loads(json.dumps(data))
            return SYSTEM_STATES[pydata]
        except Exception as e:
            print e

    def get_cpu_info(self):
        info = {}
        item = self.get_inventory('CPU')
        for cpu, info in item.items():
            for key, value in info.items():
                if key == 'Manufacturer':
                    info['Manufacturer'] = value

        print info

    def get_cpu_core_count(self):
        cores = []
        item = self.get_inventory('CORE')
        for core, info in item.items():
            for key, value in info.items():
                if key == 'present' and value == 'True':
                    cores.append('core')
        return len(cores)

    def get_chassis_info(self):
        """Return a dictonary containng SerialNumber, UUID, PartNumber, and
        Name"""
        info = {}
        item = self.get_inventory('MEMORY_BUFFER')
        for chassis, detail in item.items():
            for key, value in detail.items():
                val = str(value)
                if key == 'Custom Field 1':
                    info['UUID'] = val
                elif key == 'Manufacturer':
                    info['Manufacturer'] = val
                elif key == 'Name':
                    info['Model'] = val
                elif key == 'Part Number':
                    info['PartNumber'] = val
                elif key == 'Serial Number':
                    info['SerialNumber'] = val
        return info

    def power_control(self, name):
        if name in POWER_CONTROL.keys():
            method_name = POWER_CONTROL[name]
            obj = self.bus.get_object('org.openbmc.control.Chassis',
                                      '/org/openbmc/control/chassis0')
            intf = dbus.Interface(obj, 'org.openbmc.control.Chassis')
            mthd = obj.get_dbus_method(method_name,
                                       'org.openbmc.control.Chassis')
            out = mthd()
            return out
        else:
            print "Command %s not found" % name

    def get_system_id(self):
        obj = self.bus.get_object('org.openbmc.control.Chassis',
                                  '/org/openbmc/control/chassis0')
        intf = dbus.Interface(obj, "org.freedesktop.DBus.Properties")
        props = intf.GetAll('org.openbmc.control.Chassis')
        for p in props:
            if p == 'uuid':
                return str(props[p])

    def led_operation(self, op, led_type):
        if led_type in LED_TYPE:
            interface = '/org/openbmc/control/led/' + str(led_type)
            obj = self.bus.get_object('org.openbmc.control.led',
                                      interface)
            intf = dbus.Interface(obj, 'org.openbmc.Led')
            mthd = getattr(intf, LED_FUNCTIONS[op])
            try:
                data = mthd()
            except Exception as e:
                print e
            if data is not None:
                pydata = json.loads(json.dumps(data))
                if (isinstance(pydata, list)):
                    status = str(pydata[1])
                    if status == 'On':
                        return 'Lit'
                    else:
                        return 'Off'
                else:
                    return pydata
            else:
                return None
        else:
            return None

# Not working yet
    def get_host_settings(self):
        obj = self.bus.get_object('org.openbmc.settings.Host',
                                  '/org/openbmc/settings/host0')
        intf = dbus.Interface(obj, 'org.freedesktop.Dbus.Properties')
        data = intf.GetAll('org.openbmc.settings.Host')
        self.fix_byte(data, None, None)
        pydata = json.loads(json.dumps(data))
        print pydata

    def set_max_fan_speed(self):
        obj = self.bus.get_object('org.openbmc.control.Fans',
                                  '/org/openbmc/control/fans')
        intf = dbus.Interface(obj, 'org.openbmc.control.Fans')
        data = intf.setMax()

    def get_fan_speed(self):
        obj = self.bus.get_object('org.openbmc.control.Fans',
                                  '/org/openbmc/control/fans')
        intf = dbus.Interface(obj, "org.freedesktop.DBus.Properties")
        data = intf.GetAll('org.openbmc.control.Fans')
        self.fix_byte(data, None, None)
        pydata = json.loads(json.dumps(data))
        print pydata


# providers = ObmcRedfishProviders()
#
# print providers.get_system_id()
# print providers.power_control('state')
# providers.get_system_state()
# providers.get_fan_speed()
# providers.get_cpu_info()
# # get_host_settings()
# print 'Number of cores: %d' % providers.get_cpu_core_count()
# print providers.get_chassis_info()
#
# for inventory_item in INVENTORY_ITEMS:
#     item = providers.get_inventory(inventory_item)
#     print ">>>>>>INVENTORY>>>>>>>>>>>>>>>>>>>>>"
#     providers.print_dict("", item)
#
# for sensors in SENSORS_INFO.keys():
#     value = providers.get_sensors(sensors)
#     providers.print_dict("", value)
#
# # get_inventory()
# # get_sensors()
