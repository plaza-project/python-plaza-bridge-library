import hashlib

BUFFER_SIZE = 64 << 10  # 64KB

KNOWN_TYPES = {
    str: "string",
    bool: "boolean",
    int: "integer",
    float: "number",
}


def serialize_type(_type):
    if _type is None:
        return None

    assert isinstance(_type, type)

    if _type not in KNOWN_TYPES:
        raise Exception("Unknown type: {}".format(_type))

    return KNOWN_TYPES[_type]


def get_file_hash(f):
    # Save current position to restore in the end
    pos = f.tell()

    # Move to the start and hash all file
    f.seek(0)
    hashing = hashlib.sha256()

    while True:
        data = f.read(BUFFER_SIZE)
        if not data:
            break
        hashing.update(data)

    # Go back to previous position
    f.seek(pos)

    return ("sha256", hashing.hexdigest())
