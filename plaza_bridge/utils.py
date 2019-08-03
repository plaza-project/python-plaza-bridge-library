KNOWN_TYPES = {
    str: "string",
    bool: "boolean",
    int: "integer",
    float: "number",
}

def serialize_type(_type):
    if _type is None:
        return None

    assert(isinstance(_type, type))

    if _type not in KNOWN_TYPES:
        raise Exception("Unknown type: {}".format(_type))

    return KNOWN_TYPES[_type]
