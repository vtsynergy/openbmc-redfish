"""
 Author: Anshuman Verma
 Date  : Oct 5, 2016
 Description : Resource for Redfish
 Redfish Resource Types
"""

import json
from obmc_redfish_providers import *
from redfish_eventer import *
from redfish_message_registry import *

REDFISH_VERSION = str("1.0.3")
REDFISH_COPY_RIGHT = ("Copyright 2014-2016 Distributed Management "
                      "Task Force, Inc. (DMTF). For the full DMTF "
                      "copyright policy, see "
                      "http://www.dmtf.org/about/policies/copyright.")

REDFISH_SCHEMA_WEB_LINK = "http://redfish.dmtf.org/schemas/v1"
ODATA_ID = "@odata.id"
ODATA_TYPE = "@odata.type"
ODATA_CONTEXT = "@odata.context"


ERROR_REGISTRY_FILE_LOCATION = 'error_message_registry.json'
REGISTRY_FILES = [ERROR_REGISTRY_FILE_LOCATION]


def print_dict(name, data):
    if (isinstance(data, dict)):
        print ">>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>"
        print name
        for p in sorted(data.keys()):
            print_dict(p, data[p])
    else:
        print name+" = "+str(data)


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

        self.name = name
        """name for the class that specifies the Path to resource"""

        self.static_data_filled = 0
        """Flag to show if the static data was filled in attrs dict, update
        the flag when the static data is filled, would be updated when the
        resource is queried for the first time"""

        self.self_metadata_path = ""
        """Hardcoded the above, need to get it updated when adding metadata
        functionality"""

        self.child_metadata_path = ""

        self.namespace = ""

        self.version = ""

        self.is_leaf = False
        """Flag to show if the node if a leaf, useful for objects that are
        embedded into a node"""

        self.message_registry = MessageRegistry(REGISTRY_FILES)

    def get_redfish_web_link(self):
        """Returns the link of online schema at redfish website, use it to
        create metadata document"""
        path_list = self.version.split(".")
        if len(path_list) == 1:
            path_list[0] = ""
        else:
            path_list[0] = path_list[0] + "."

        web_link = (REDFISH_SCHEMA_WEB_LINK + "/" + self.namespace +
                    "." + path_list[0] + "json")
        return web_link

    def get_document(self):
        doc = {}
        doc["name"] = self.name
        doc["kind"] = "singleton"
        doc["url"] = self.path
        doc["reference"] = self.get_redfish_web_link()
        return doc

    def update_metadata_path(self):
        self.self_metadata_path = (self.parent.child_metadata_path +
                                   "$entity")
        self.child_metadata_path = (self.parent.self_metadata_path +
                                    "/" + self.name + "/")

    def add_child(self, obj):
        """Add a child to the node"""
        self.child.append(obj)
        obj.parent = self
        obj.provider = self.provider
        if obj.is_leaf is False:
            obj.path = str(self.path + "/" + obj.name)
            obj.update_metadata_path()
        else:
            obj.path = str(self.path + "#/" + obj.name)
        obj.attrs[ODATA_ID] = obj.path

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
        if self.is_leaf is False:
            self.attrs[ODATA_CONTEXT] = self.self_metadata_path
            self.attrs[ODATA_TYPE] = "#" + self.namespace + "." + self.version
            self.attrs["@Redfish.Copyright"] = REDFISH_COPY_RIGHT

    def fill_dynamic_data(self):
        """Update or fill the attributes of attrs dictonary when a get request
        is recieved. Extend in inherited classes"""
        pass

    def add_related_object(self, name, obj):
        """Add a related object to this item"""
        if "Links" not in self.attrs:
            self.attrs["Links"] = {}
        if name not in self.attrs["Links"]:
            self.attrs["Links"][name] = []
        self.attrs["Links"][name].append(dict([(ODATA_ID, obj.path)]))

    def get_export_data(self, op):
        """Export the json data to server"""
        """FIXME: this with correct functions calls in case of error"""
        if op[0] != self.name or len(op) == 0:
            print "Error:" + self.name + str(len(op)) + str(op[0])
            return self.message_registry.get_error_message(
                    ERROR_REGISTRY_FILE_LOCATION,
                    "ResourceDoesNotExist", op[0])
        elif len(op) > 1:
            for children in self.child:
                if children.name == op[1]:
                    op.pop(0)
                    return children.get_export_data(op)
            else:
                return self.message_registry.get_error_message(
                        ERROR_REGISTRY_FILE_LOCATION,
                        "ResourceDoesNotExist", op[1])
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
            return self.message_registry.get_error_message(
                    ERROR_REGISTRY_FILE_LOCATION, "ResourceDoesNotExist",
                    path[0])
        elif len(path) > 3:
            for children in self.child:
                if children.name == path[1]:
                    path.pop(0)
                    return children.action(path, op)
            else:
                return self.message_registry.get_error_message(
                        ERROR_REGISTRY_FILE_LOCATION, "ResourceDoesNotExist",
                        path[1])
        else:
            if path[1] != 'Actions':
                return self.message_registry.get_error_message(
                        ERROR_REGISTRY_FILE_LOCATION, "ResourceDoesNotExist",
                        path[1])
            else:
                action_list = path[2].split('.')
                uri_namespace = action_list[0]
                action = action_list[1]
                action_type = action + "Type"
                if self.static_data_filled == 0:
                    self.fill_static_data()
                    self.static_data_filled = 1
                self.fill_dynamic_data()
                print action
                print action_type
                if action in self.actions.keys():
                    try:
                        method = getattr(self, str(action.lower()))
                        try:
                            method_arg = op.json[action_type]
                            print method_arg
                        except ValueError:
                            return self.message_registry.get_error_message(
                                    ERROR_REGISTRY_FILE_LOCATION,
                                    "PropertyValueNotInList",
                                    action, "Method does not exist")
                        if method_arg is None:
                            return self.message_registry.get_error_message(
                                    ERROR_REGISTRY_FILE_LOCATION,
                                    "PropertyValueNotInList",
                                    action, "None")
                        if method_arg in self.actions[action]:
                            print "Argument is " + str(method_arg)
                            method(method_arg)
                        else:
                            return self.message_registry.get_error_message(
                                    ERROR_REGISTRY_FILE_LOCATION,
                                    "PropertyValueNotInList",
                                    action, method_arg)
                    except AttributeError:
                        return self.message_registry.get_error_message(
                                ERROR_REGISTRY_FILE_LOCATION,
                                "ResourceDoesNotExist",
                                action)
                else:
                    return self.message_registry.get_error_message(
                            ERROR_REGISTRY_FILE_LOCATION,
                            "ResourceDoesNotExist",
                            action)
                print uri_namespace + action + str(op.POST.items())
                return

    def add_action(self, act, op):
        if(isinstance(op, list)):
            self.actions[act] = op
            suffix = self.namespace + "." + act
            key = "#" + suffix
            target = self.path + "/Actions/" + suffix
            allowed_values = act + "Type@Redfish.AllowableValues"
            if 'Actions' not in self.attrs:
                self.attrs['Actions'] = {}
            self.attrs['Actions'][key] = dict([('target', target),
                                               (allowed_values, op)])
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
        super(RedfishCollectionBase, self).fill_static_data()
        self.attrs["Members"] = []
        for children in self.child:
            self.attrs["Members"].append(dict([(ODATA_ID, children.path)]))

    def update_metadata_path(self):
        self.self_metadata_path = (self.parent.child_metadata_path +
                                   self.name)
        self.child_metadata_path = self.self_metadata_path + "/Members/"


class RedfishRoot(RedfishBase):
    """Root object for redfish, located at 'redfish'"""

    def __init__(self, name, provider):
        super(RedfishRoot, self).__init__(name)
        self.path = str("/" + name)
        self.provider = provider
        self.child_metadata_path = self.path
        self.self_metadata_path = self.path

    def add_child(self, ob):
        """When adding child for root, delete all the attributes"""
        super(RedfishRoot, self).add_child(ob)
        for key in self.attrs.keys():
            del self.attrs[key]
        self.attrs[ob.name] = ob.path

    def fill_static_data(self):
        pass


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

    def update_metadata_path(self):
        self.child_metadata_path = self.path + "/$metadata#"
        self.self_metadata_path = self.child_metadata_path + self.namespace

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


class SystemCollection(RedfishCollectionBase):
    """Computer System Collection class"""

    def __init__(self, name, instance_id):
        super(SystemCollection, self).__init__(name)
        self.instance_id = instance_id
        self.namespace = "ComputerSystemCollection"
        self.version = "ComputerSystemCollection"

    def fill_static_data(self):
        super(SystemCollection, self).fill_static_data()
        self.attrs["Name"] = self.instance_id


class ChassisCollection(RedfishCollectionBase):
    """Chassis Collection"""

    def __init__(self, name, instance_id):
        super(ChassisCollection, self).__init__(name)
        self.instance_id = instance_id
        self.namespace = "ChassisCollection"
        self.version = "ChassisCollection"

    def fill_static_data(self):
        super(ChassisCollection, self).fill_static_data()
        self.attrs["Name"] = self.instance_id


class Chassis(RedfishBase):
    """Chassis Information"""

    def __init__(self, name, argv):
        super(Chassis, self).__init__(name)
        self.namespace = "Chassis"
        self.version = "v1_0_3.Chassis"
        for keys in argv.keys():
            if keys is not "UUID":
                self.attrs[keys] = argv[keys].strip()

    def fill_static_data(self):
        super(Chassis, self).fill_static_data()
        self.attrs["Id"] = self.name
        self.add_action("LedUpdate", ['On',
                                      'Off',
                                      'BlinkFast',
                                      'BlinkSlow'])
        for children in self.child:
            self.attrs[children.name] = dict([(ODATA_TYPE, children.path)])

    def ledupdate(self, op):
        self.provider.led_operation(op, 'identify')

    def fill_dynamic_data(self):
        super(Chassis, self).fill_dynamic_data()
        led_state = self.provider.led_operation('State', 'identify')
        if led_state is not None:
            self.attrs['IndicatorLed'] = led_state
        self.attrs['PowerState'] = self.provider.get_system_state()


class System(RedfishBase):
    """System Information"""

    def __init__(self, name, argv):
        super(System, self).__init__(name)
        self.namespace = "ComputerSystem"
        self.version = "v1_0_3.ComputerSystem"
        for keys in argv.keys():
            if keys is "UUID":
                uuid = argv[keys].split(':')
                if len(uuid) > 1:
                    self.attrs[keys] = self.fancy_uuid(uuid[1])
            else:
                self.attrs[keys] = argv[keys].strip()

    def fill_static_data(self):
        super(System, self).fill_static_data()
        self.attrs["Id"] = self.name
        self.attrs["SystemType"] = self.provider.get_system_type()
        self.attrs["BiosVerion"] = self.provider.get_bios_version()
        self.add_action("Reset", ['On',
                                  'ForceOff',
                                  'GracefulShutDown',
                                  'ForceRestart'
                                  'GracefulRestart'])
        self.add_action("LedUpdate", ['On',
                                      'Off',
                                      'BlinkFast',
                                      'BlinkSlow'])
        for children in self.child:
            self.attrs[children.name] = dict([(ODATA_TYPE, children.path)])

    def reset(self, op):
        self.provider.power_control(op)

    def ledupdate(self, op):
        self.provider.led_operation(op, 'identify')

    def fill_dynamic_data(self):
        super(System, self).fill_dynamic_data()
        led_state = self.provider.led_operation('State', 'identify')
        if led_state is not None:
            self.attrs['IndicatorLed'] = led_state
        self.attrs['PowerState'] = self.provider.get_system_state()


class EventService(RedfishBase):
    """Event Service Resource"""

    def __init__(self, name):
        super(EventService, self).__init__(name)
        self.namespace = "EventService"
        self.version = "v1_0_2.EventService"
        self.attrs["ServiceEnabled"] = True
        self.attrs["Name"] = "Event Service"


class EventDestinationCollection(RedfishCollectionBase):
    """Event Destination Collection class"""

    def __init__(self, name):
        super(EventDestinationCollection, self).__init__(name)


class ErrorRegistryFile(EventService):
    """Error Registry File Resource"""

    def __init__(self, name, location):
        super(EventService, self).__init__(name)
        self.attrs["Location"] = location


class RegistryFileCollection(RedfishCollectionBase):
    """Registry File Collection"""

    def __init__(self, name):
        super(RegistryFileCollection, self).__init__(name)


class Registries(RedfishCollectionBase):
    """Message Registries Collection class"""

    def __init__(self, name):
        super(Registries, self).__init__(name)


class ProcessorCollection(RedfishCollectionBase):
    """Class for Collection of Processors"""

    def __init__(self, name, instance_id):
        super(ProcessorCollection, self).__init__(name)
        self.instance_id = instance_id
        self.namespace = "ProcessorCollection"
        self.version = "ProcessorCollection"

    def fill_static_data(self):
        super(ProcessorCollection, self).fill_static_data()
        self.attrs["Name"] = self.instance_id


class Processor(RedfishBase):
    """CPU Information"""

    def __init__(self, name, argv):
        super(Processor, self).__init__(name)
        self.namespace = "Processor"
        self.version = "v1_0_2.Processor"
        self.attrs["Id"] = name
        for keys in argv.keys():
            if keys == 'UUID':
                argv[keys] = self.fancy_uuid(argv[keys])
            self.attrs[keys] = argv[keys]


class MemoryCollection(RedfishCollectionBase):
    """Class for Collection of Memorys"""

    def __init__(self, name, instance_id):
        super(MemoryCollection, self).__init__(name)
        self.instance_id = instance_id
        self.namespace = "MemoryCollection"
        self.version = "MemoryCollection"

    def fill_static_data(self):
        super(MemoryCollection, self).fill_static_data()
        self.attrs["Name"] = self.instance_id


class Memory(RedfishBase):
    """CPU Information"""

    def __init__(self, name, argv):
        super(Memory, self).__init__(name)
        self.attrs["Id"] = name
        self.namespace = "Memory"
        self.version = "v1_0_0.Memory"
        for keys in argv.keys():
            self.attrs[keys] = argv[keys]


class Power(RedfishBase):
    """CPU Information"""

    def __init__(self, name):
        super(Power, self).__init__(name)
        self.attrs["Id"] = name
        self.namespace = "Power"
        self.version = "v1_2_0.Power"
        self.powercontrol = []
        self.powersupplies = []

    def add_child(self, obj):
        super(Power, self).add_child(obj)
        if isinstance(obj, PowerControl) is True:
            self.powercontrol.append(obj)
        if isinstance(obj, PowerSupplies) is True:
            self.powersupplies.append(obj)

    def fill_dynamic_data(self):
        super(Power, self).fill_dynamic_data()
        self.attrs["PowerControl"] = []
        self.attrs["PowerSupplies"] = []
        for p in self.powercontrol:
            p.fill_dynamic_data()
            self.attrs["PowerControl"].append(p.attrs)
        for p in self.powersupplies:
            p.fill_dynamic_data()
            self.attrs["PowerSupplies"].append(p.attrs)


class Thermal(RedfishBase):
    """CPU Information"""

    def __init__(self, name):
        super(Thermal, self).__init__(name)
        self.attrs["Id"] = name
        self.namespace = "Thermal"
        self.version = "v1_1_0.Thermal"


class PowerSupplies(RedfishBase):
    """Power Control Information"""

    def __init__(self, name, instance_id):
        super(PowerSupplies, self).__init__(name)
        self.attrs["Id"] = name
        self.attrs["Name"] = instance_id
        self.is_leaf = True

    def fill_dynamic_data(self):
        self.attrs["PowerSupplyType"] = "TBD"
        self.attrs["LineInputVoltageType"] = "TBD"
        self.attrs["LineInputVoltage"] = -100
        self.attrs["PowerCapacityWatts"] = -900
        self.attrs["LastPowerOutputWatts"] = -900
        self.attrs["Model"] = "TBD"
        self.attrs["Manufacturer"] = "TBD"
        self.attrs["FirmwareVersion"] = "TBD"
        self.attrs["SerialNumber"] = "TBD"
        self.attrs["PartNumber"] = "TBD"
        self.attrs["SparePartNumber"] = "TBD"
        self.attrs["InputRanges"] = [{"InputType": "TBD",
                                      "MininmumVoltage": -100,
                                      "MaximumVoltage": -100,
                                      "OutputWattage": -100},
                                     {"InputType": "TBD",
                                      "MininmumVoltage": -100,
                                      "MaximumVoltage": -100,
                                      "OutputWattage": -100}]


class PowerControl(RedfishBase):
    """Power Control Information"""

    def __init__(self, name, instance_id):
        super(PowerControl, self).__init__(name)
        self.attrs["Id"] = name
        self.attrs["Name"] = instance_id
        self.is_leaf = True

    def fill_dynamic_data(self):
        self.attrs["PowerConsumedWatts"] = -100
        self.attrs["PowerRequestedWatts"] = -100
        self.attrs["PowerAvaiableWatts"] = -100
        self.attrs["PowerCapacityWatts"] = -900
        self.attrs["PowerAllocatedWatts"] = -900
        self.attrs["PowerMetrics"] = {"IntervalInMin": -100,
                                      "MinConsumedWatts": -100,
                                      "MaxConsumedWatts": -100,
                                      "AverageConsumedWatts": -100}
        self.attrs["PowerLimit"] = {"LimitInWatts": -100,
                                    "LimitException": "LogEventOnly",
                                    "CorrectionInMs": -100}
        self.attrs["Status"] = {"State": "Enabled",
                                "Health": "NOT OK"}


class RedfishBottleRoot(object):
    """Class that contains and builds the resource tree"""

    def __init__(self):
        """Build the resource tree in a top-down fashion"""
        self.provider = ObmcRedfishProviders()

        self.eventer = Eventer(False, 3, 5)

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

        self.system = System(self.chassis_info['SerialNumber'],
                             self.chassis_info)

        self.system_collection.add_child(self.system)

        self.chassis = Chassis("1U", self.chassis_info)

        self.chassis_collection.add_child(self.chassis)

        self.chassis.add_related_object("ComputerSystems", self.system)

        self.processors = ProcessorCollection("Processors",
                                              "Processors Collection")

        self.system.add_child(self.processors)

        self.memories = MemoryCollection("Memory",
                                         "Memory Collection")

        self.system.add_child(self.memories)

        self.processor_list = []

        self.processor_dict = self.provider.get_cpu_info()

        self.index = 0

        for keys in self.processor_dict.keys():
            self.processor_list.append(Processor(keys,
                                       self.processor_dict[keys]))
            self.processors.add_child(self.processor_list[self.index])
            self.index = self.index + 1

        self.index = 0

        self.memory_list = []

        self.memory_dict = self.provider.get_dimm_info()

        for keys in self.memory_dict.keys():
            self.memory_list.append(Memory(keys,
                                    self.memory_dict[keys]))
            self.memories.add_child(self.memory_list[self.index])
            self.index = self.index + 1

        self.index = 0

        self.registries = Registries("Base Message Registry File")

        self.v1.add_child(self.registries)

        self.event_service = EventService("EventService")

        self.v1.add_child(self.event_service)

        self.event_destination_collection = \
            EventDestinationCollection("Event Subscriptions Collection")

        self.event_service.add_child(self.event_destination_collection)

        self.registry_file_collection = \
            RegistryFileCollection("Registry Files Collection")

        self.v1.add_child(self.registry_file_collection)

        self.error_registry_file = \
            ErrorRegistryFile("Error Registry File",
                              ERROR_REGISTRY_FILE_LOCATION)

        self.registry_file_collection.add_child(self.error_registry_file)

        self.thermal = Thermal("Thermal")

        self.chassis.add_child(self.thermal)

        self.power = Power("Power")

        self.chassis.add_child(self.power)

        self.power_control = PowerControl("PowerControl", "Power Control")

        self.power_supplies_0 = PowerSupplies("0", "Power Supplies")
        self.power_supplies_1 = PowerSupplies("1", "Power Supplies")

        self.power.add_child(self.power_control)
        self.power.add_child(self.power_supplies_0)
        self.power.add_child(self.power_supplies_1)
#       Experimental code for sensors. Would remove this later
#        self.provider.get_fan_speed()
        for sensors in SENSORS_INFO.keys():
            value = self.provider.get_sensors(sensors)
            print_dict("", value)

    def print_all(self):
        self.root.print_all()

    def get_odata_document(self):
        q = []
        document = {}
        document[ODATA_CONTEXT] = '/redfish/v1/$metadata'
        document['value'] = []
        q.append(self.root)
        while len(q):
            children = q.pop(-1)
            document['value'].append(children.get_document())
            for subchild in children.child:
                q.append(subchild)
        return json.dumps(document)

    def get_json(self, path):
        if len(path) == 3 and path[0] == 'redfish' \
                and path[1] == 'v1' and path[2] == '$metadata':
                    return self.get_odata_document()
        else:
            return self.root.get_export_data(path)

    def do_action(self, path, obj):
        return self.root.action(path, obj)
