class ServiceBlock:
    def __init__(self, function_name, message, arguments=[]):
        self.function_name = function_name
        self.message = message
        self.arguments = arguments

    def serialize(self):
        return {
            "function_name": self.function_name,
            "message": self.message,
            "arguments": list(map(lambda a: a.serialize(), self.arguments)),
        }


ALLOWED_ARGUMENT_TYPES = {
    str: "string",
    int: "integer",
    float: "float",
    bool: "boolean",
}


class BlockArgument:
    def __init__(self, type, default):
        if type not in ALLOWED_ARGUMENT_TYPES:
            raise TypeError("Type “{}” not allowed".format(type))

        self.type = type
        self.default = default

    def serialize(self):
        return {"type": ALLOWED_ARGUMENT_TYPES[self.type], "default": self.default}

