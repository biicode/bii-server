from biicode.common.settings.fixed_string import FixedStringWithValue
import datetime


class RestActionType(FixedStringWithValue):
    '''Mapping of actions and store numbers'''
    map_values = {'GET_PUBLISHED_RESOURCES': 0,
                  'CREATE_BLOCK': 1,
                  'PUBLISH': 2,
                  'GET_DEP_TABLE': 4,
                  'GET_CELLS_SNAPSHOT': 5,
                  'FIND': 6,
                  'DIFF': 7,
                  'FIND_PATH': 8,
                  'FIND_COMMON_ROOT': 9,
                  'GET_RENAMES': 10,
                  'TEST': 11,  # Deprecated
                  'CHECK_CAN_PUBLISH': 12,  # Deprecated
                  'GET_LAST_VERSION': 13,  # Deprecated
                  'READ_HIVE': 14,
                  'UPLOAD': 15,
                  'READ_EDITION_CELLS': 16,
                  'READ_EDITION_CONTENTS': 17,
                  'GET_VERSION_DELTA_INFO': 18,
                  'GET_BLOCK_INFO': 19,
                  'AUTHENTICATE': 20,
                  'GET_SERVER_INFO': 21,
                  'REQUIRE_AUTH': 22}


class WebActionType(FixedStringWithValue):
    '''Mapping of actions and store numbers'''
    map_values = {'SIMPLE_SEARCH': 7,  # Begin with 7, 6 and under are old web values
                  'OTHER': 99
                  }


class GroupType(FixedStringWithValue):
    '''Different types of group of user traced actions'''
    map_values = {'REST': 0, 'WEB': 1}
    action_type_class = {'REST': RestActionType, 'WEB': WebActionType}


class UserTracedAction(object):
    '''Model for a generic user action (represent the data of the request)'''

    def __init__(self, group_name, action_name, ip_address, login, anonymous_user_token=None, description="", date_time=None):
        self.date_time = date_time or datetime.datetime.now()
        self.ip_address = ip_address
        self.description = description
        self.login = login
        self.anonymous_user_token = anonymous_user_token
        self.action_name = action_name

        self.group_id = None
        self.task_id = None

        if group_name is not None:
            self.group_id = GroupType(group_name).value
        if action_name is not None:
            self.task_id = GroupType.action_type_class[GroupType(group_name)](action_name).value

    @staticmethod
    def deserialize(data):
        '''Create a object from data'''
        obj = UserTracedAction(None, None, data["ip"], data["login"],
                               data["anonymous_user_token"], data["description"], data["datetime"])
        obj.group_id = data["group_id"]
        obj.task_id = data["task_id"]
        obj.action_name = data["action_name"]
        return obj

    def serialize(self):
        '''return a tuple with the data'''
        return {"group_id": self.group_id,
                "task_id": self.task_id,
                "ip": self.ip_address,
                "login": self.login,
                "description": str(self.description),
                "anonymous_user_token": self.anonymous_user_token,
                "datetime": self.date_time,
                "action_name": self.action_name}

    def __eq__(self, other):
        return other is not None \
            and self.__class__ == other.__class__ \
            and self.serialize() == other.serialize()

    def __ne__(self, other):
        return not self.__eq__(other)

    def __repr__(self):
        return str(self.serialize())
