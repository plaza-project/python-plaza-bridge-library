import enum


class BlockType(enum.Enum):
    TRIGGER = "trigger"
    OPERATION = "operation"
    GETTER = "getter"


class ServiceBlock:
    def __init__(
        self,
        id,
        function_name,
        message,
        block_type,
        block_result_type=None,
        arguments=[],
    ):
        self.id = id
        self.function_name = function_name
        self.message = message
        self.block_type = block_type
        self.block_result_type = block_result_type
        self.arguments = arguments

    def serialize(self):
        return {
            "id": self.id,
            "function_name": self.function_name,
            "message": self.message,
            "arguments": list(map(lambda a: a.serialize(), self.arguments)),
            "block_type": self.block_type.value,
            "block_result_type": self.block_result_type,
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
