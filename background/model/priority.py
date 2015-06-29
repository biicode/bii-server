from biicode.common.settings.fixed_string import FixedString


class Priority(FixedString):
    '''Fixed names for queue priority'''
    values = ["low", "medium", "high"]
