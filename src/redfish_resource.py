#! /usr/bin/env python

# Author: Anshuman Verma
# Date  : Oct 5, 2016
# Description : Resource for Redfish

import sys
import json

"""
Redfish Resource Types
"""

REDFISH_VERSION = str("1.0.3")
REDFISH_COPY_RIGHT = ("Copyright 2014-2016 Distributed Management "
                      "Task Force, Inc. (DMTF). For the full DMTF "
                      "copyright policy, see "
                      "http://www.dmtf.org/about/policies/copyright.")


class RedfishBase(object):
    """Base class for Redfish Obejcts"""

    def __init__(self, name):

        self.attrs = {}
        """Dictionary of redfish attributes"""

        self.child = []
        """List of children resources"""

        self.related_object = []
        """List of related objects"""

        self.name = name
        """name for the class that specifies the Path to resource"""

        self.attrs["@Redfish.Copyright"] = REDFISH_COPY_RIGHT

    def add_child(self, obj):
        """Add a child to the node"""
        self.child.append(obj)
        obj.path = str(self.path + "/" + obj.name)
        obj.parent = self
        obj.attrs["@odata.id"] = obj.path

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

    def add_related_object(self, obj):
        """Add a related object to this item"""
        self.related_object.append(obj)

    def get_export_data(self, op):
        """Export the json data to server"""
        """FIXME: this with correct functions calls in case of error"""
        if op[0] != self.name or len(op) == 0:
            print "Error:" + self.name + str(len(op)) + str(op[0])
            return "Error"
        elif len(op) > 1:
            for children in self.child:
                if children.name == op[1]:
                    op.pop(0)
                    return children.get_export_data(op)
            else:
                return "Error"
        else:
            return json.dumps(self.attrs)

    def action(self,path,op):
        """Perfrom the requested action and return the information"""
        """FIXME: Fill in the details for Error Class"""
        if path[0] != self.name or len(path) == 1: 
            print "[ACTION] Error: " + self.name + str(len(op)) + str(op[0])
        elif len(path) > 3:
            for children in self.child:
                if children.name == path[1]:
                    path.pop(0)
                    return children.action(path,op)
            else:
                return "Error [ACTION]: Path not correct"
        else:
            if path[1] != 'Action':
                return "Error: Action URI is incorrect"
            else: 
                action_list = path[2].split('.')
                uri_namespace = action_list[0]
                action = action_list[1]
                print uri_namespace + action + str(op.POST.items())
                return 



class RedfishCollectionBase(RedfishBase):
    """Base class for Redfish Collections"""

    def __init__(self, name):
        super(RedfishCollectionBase, self).__init__(name)
        self.attrs["Members@odata.count"] = 0

    def add_child(self, obj):
        super(RedfishCollectionBase, self).add_child(obj)
        self.attrs["Members@odata.count"] += 1


class RedfishRoot(RedfishBase):
    """Root object for redfish"""

    def __init__(self, name):
        super(RedfishRoot, self).__init__(name)
        self.path = str("/" + name)

    def add_child(self, ob):
        """When adding child for root, delete all the attributes"""
        super(RedfishRoot, self).add_child(ob)
        for key in self.attrs.keys():
            del self.attrs[key]
        self.attrs[ob.name] = ob.path

class RootManager(RedfishBase):
    """Root Manager for Redfish"""

    def __init__(self, name):
        super(RootManager, self).__init__(name)


class ChassisManager(RedfishCollectionBase):
    """Chassis Manager"""

    def __init__(self, name):
        super(ChassisManager, self).__init__(name)

class ChassisInstance(RedfishBase):
    """Chassis Information"""
    
    def __init__(self, name):
        super(ChassisInstance, self).__init__(name)


class SystemInstance(RedfishBase):
    """System Information"""

    def __init__(self, name):
        super(SystemInstance, self).__init__(name)


class CpuInstance(RedfishBase): 
    """CPU Information"""

    def __init__(self, name): 
        super(CpuInstance, self).__init__(name)



class RedfishBottleRoot(object):
    """Class that contains and builds the resource tree"""

    def __init__(self):
        """Build the resource tree in a top-down fashion"""
        self.root = RedfishRoot("redfish")

        self.v1 = RootManager("v1")
        self.root.add_child(self.v1)

        self.chassis_m = ChassisManager("Chassis")
        self.v1.add_child(self.chassis_m)

    def print_all(self):
        self.root.print_all()

    def get_json(self, path):
        return self.root.get_export_data(path)

    def do_action(self, path, obj):
        return self.root.action(path, obj)
