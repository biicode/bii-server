import uuid


def generate_str_unique_id():
    """Creates a unique id using uuid and returns a str representation"""
    return str(uuid.uuid1().int)
