
class StaticData(dict):
    '''A dict of data'''

    def serialize(self):
        return self

    @staticmethod
    def deserialize(data):
        return StaticData(data)

