"""
 Author:  Anshuman Verma (anshuman@vt.edu)
 Date   :  Aug 26th, 2016
 Description:
"""

import json
import dbus
import obmc.mapper
import obmc.utils.misc


POWER_CONTROL = {'On': 'powerOn',
                 'ForceOff': 'powerOff',
                 'GracefulShutDown': 'softPowerOff',
                 'ForceRestart': 'reboot',
                 'GracefulRestart': 'softReboot',
                 'State': 'getPowerState'
                 }


SENSORS_INFO = {'AMBIENT': 'ambient',
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
SYSTEM_STATES = {'BASE_APPS': "Off",
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
                 'State': 'GetLedState'}

LED_TYPE = ['identify', 'power', 'heartbeat']

# FIXME : Remove this later, keeping it to know the names of items
# INVENTORY_ITEMS = ['SYSTEM',
#                    'MAIN_PLANAR',
#                    'FAN',
#                    'BMC',
#                    'CPU',
#                    'CORE',
#                    'DIMM',
#                    'PCIE_CARD',
#                    'SYSTEM_EVENT',
#                    'MEMORY_BUFFER']

def fix_byte(it, key, parent):
    if (isinstance(it, dbus.Array)):
        for i in range(0, len(it)):
            fix_byte(it[i], i, it)
    elif (isinstance(it, dict)):
        for key in it.keys():
            fix_byte(it[key], key, it)
    elif (isinstance(it, dbus.Byte)):
        if key is not None:
            parent[key] = int(it)
    elif (isinstance(it, dbus.Double)):
        if key is not None:
            parent[key] = float(it)

def print_dict(name, data):
    if (isinstance(data, dict)):
        print ">>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>"
        print name
        for p in sorted(data.keys()):
            print_dict(p, data[p])
    else:
        print name+" = "+str(data)


class ObmcRedfishProviders(object):
    """OpenBMC Redfish Providers using DBUS"""

    def __init__(self):
        """Initialize the class"""
        self.bus = dbus.SystemBus()
        self.mapper = obmc.mapper.Mapper(self.bus)

        self.inventory_data = None

    def find_inventory_object(self, name, object):
        merged = {}
        for op in object.keys():
            for property, value in object[op].items():
                if property == 'fru_type' and \
                    value == name:
                    merged[op] = object[op]
        return merged

    def find_sensor_value(self, name, object):
        merged = {}
        for op in object.keys():
            p_op = op.split('/')
            if p_op[-1] == name:
                return object[op]

    def get_enumerated_obj(self, path='/'):
        sub_tree = self.mapper.get_subtree(path=path)
        return {x: y for x, y in self.mapper.enumerate_subtree(
                path, mapper_data=sub_tree).dataitems()}


# FIXME: FIX the return value argument
    def get_inventory(self, name):
        if self.inventory_data is None:
            try:
                data = self.get_enumerated_obj('org/openbmc/inventory')
                fix_byte(data, None, None)
                self.inventory_data = json.loads(json.dumps(data))
            except Exception as e:
                print e
                return "error"

        inventory_object = self.find_inventory_object(name,
                                                      self.inventory_data)
        return inventory_object

#FIXME: Not all sensors are implemented in this, use nameserver! 
    def get_sensors(self, sensor):
        sensor_values = {}
        sensor_values['type'] = sensor
        try:
            data = self.get_enumerated_obj('org/openbmc/sensors')
            fix_byte(data, None, None)
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
            fix_byte(data, None, None)
            pydata = json.loads(json.dumps(data))
            return SYSTEM_STATES[pydata]
        except Exception as e:
            print e

    def get_dimm_info(self):
        """Return a dictonary of DIMMs with fields set as per Redfish
        specification"""
        info = {}
        item = self.get_inventory('DIMM')
        for dimm in item.keys():
            dimm = str(dimm)
            path_list = dimm.split("/")
            dimm_inst = path_list[-1].upper()
            info[dimm_inst] = {}
            for key in item[dimm].keys():
                value = str(item[dimm][key])
                if key == 'Manufacturer':
                    info[dimm_inst]['Manufacturer'] = value
                elif key == 'fru_type':
                    info[dimm_inst]['MemoryType'] = "DRAM"
                elif key == 'Serial Number':
                    info[dimm_inst]['SerialNumber'] = value
                elif key == 'Part Number':
                    info[dimm_inst]['PartNumber'] = value
                elif key == "Name":
                    info[dimm_inst]["Name"] = value
                elif key == 'present':
                    if value == 'True':
                        info[dimm_inst]['Status'] = dict([("State", "Enabled"),
                                                         ("Health", "Ok")])
        return info

    def get_pcie_info(self):
        """Return a dictonary of PCIeDevices with fields set as per Redfish
        specification"""
        info = {}
        item = self.get_inventory('PCIE_CARD')
        for pcie in item.keys():
            pcie = str(pcie)
            path_list = pcie.split("/")
            pcie_inst = path_list[-1].upper()
            info[pcie_inst] = {}
            for key in item[pcie].keys():
                value = str(item[pcie][key])
                if key == 'present':
                    if value == "True":
                        info[pcie_inst]['Status'] = dict([("State", "Enabled"),
                                                         ("Health", "Ok")])
        return info

    def get_cpu_info(self):
        """Returns a dictonary of CPUs with fields set as per Redfish
        Specification"""
        info = {}
        item = self.get_inventory('CPU')
        for cpu, detail in item.items():
            cpu = str(cpu)
            path_list = cpu.split("/")
            cpu_inst = path_list[-1].upper()
            info[cpu_inst] = {}
            for key, value in detail.items():
                value = str(value)
                core_count = self.get_cpu_core_count(cpu_inst)
                info[cpu_inst]["TotalCores"] = core_count
                if key == 'Manufacturer':
                    info[cpu_inst]['Manufacturer'] = value
                elif key == 'fru_type':
                    info[cpu_inst]['ProcessorType'] = value
                elif key == 'Serial Number':
                    info[cpu_inst]['SerialNumber'] = value
                elif key == 'Part Number':
                    info[cpu_inst]['PartNumber'] = value
                elif key == 'Custom Field 2':
                    list_value = value.split(":")
                    info[cpu_inst]['UUID'] = list_value[1]
                elif key == "Name":
                    info[cpu_inst]["Name"] = value
                elif key == 'FRU File ID':
                    info[cpu_inst]["FRU"] = value
                elif key == 'present':
                    if value == 'True':
                        info[cpu_inst]['Status'] = dict([("State", "Enabled"),
                                                         ("Health", "Ok")])
        return info

    def get_cpu_core_count(self, cpu_id):
        cores = []
        item = self.get_inventory('CORE')
        for core, info in item.items():
            core_list = core.split("/")
            core_id = core_list[-2].upper()
            if core_id == cpu_id:
                for key, value in info.items():
                    if key == 'present' and value == 'True':
                        cores.append('core')
        return len(cores)

    def get_bios_version(self):
        item = self.get_inventory('SYSTEM')
        for system in item.keys():
            system_list = system.split("/")
            system_list[-1] = system_list[-1].upper()
            if system_list[-1] == 'SYSTEM':
                for keys in item[system]:
                    if keys == "Version":
                        return str(item[system][keys])

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
        fix_byte(data, None, None)
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
        fix_byte(data, None, None)
        pydata = json.loads(json.dumps(data))
        print pydata
