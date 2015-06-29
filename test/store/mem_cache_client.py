
class MemCacheClient:
    """Class for testing purpose. Only implements classic cache methods.
    Warning: Doesn't handle time expires"""

    def __init__(self):
        self.elements = {}
        self.read_counter = 0
        self.write_counter = 0
        self.delete_counter = 0

    def delete(self, key):
        self.delete_counter += 1
        self.elements.pop(key)

    def set(self, key, value, time=None):
        self.write_counter += 1
        self.elements[key] = value

    def get(self, key):
        self.read_counter += 1
        return self.elements[key]
