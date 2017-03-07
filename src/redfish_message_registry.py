# Description : Message Registry for OpenBMC Redfish

import json


class MessageRegistry(object):

    """Base class for Redfish Message Registries"""

    def __init__(self, registries_on_file=[]):
        self.registries = registries_on_file

    def get_message(self, registry_id, message_id, args):
        """
        Provided there is a registry with 'registry_id' and a message in that
        registry with id, 'message_id', then the args for that message
        will be interpolated into that message and packaged into 'Message' 4
        representation.
        """

        if registry_id in self.registries:
            with open(registry_id) as registry_file:
                registry = json.load(registry_file)
                if message_id in registry['Messages']:
                    message = registry['Messages'][message_id]
                    msg_str = message['Message']
                    message['Message'] = self.interpolate_message_args(
                                                msg_str,
                                                args)
                    return message
                else:
                    return {'Message': 'no message match'}
        else:
            return {'Message': 'no registry match'}

    def get_extended_messages(self, ext_msg_info_arr=[]):
        extended_info = {'@Message.ExtendedInfo': []}
        for ext_msg_info in ext_msg_info_arr:
            extended_info['@Message.ExtendedInfo'].append(
                        self.get_message(
                            ext_msg_info[0],
                            ext_msg_info[1],
                            ext_msg_info[2])
                    )
        return extended_info

    def interpolate_message_args(self, message, args):
        for i, arg in enumerate(args):
            message = message.replace('%'+str(i+1), arg)
        return message
