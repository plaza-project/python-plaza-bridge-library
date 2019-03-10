import enum


class BlockContextArgument:
    def __getitem__(self, index):
        return {"type": "argument", "index": index}


class BlockContextClass:
    def __init__(self):
        self.ARGUMENTS = BlockContextArgument()


BlockContext = BlockContextClass()


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


class ServiceTriggerBlock:
    def __init__(self, id, function_name, message, arguments=[], save_to=None):
        self.id = id
        self.function_name = function_name
        self.message = message
        self.arguments = arguments
        self.save_to = save_to

    def serialize(self):
        return {
            "id": self.id,
            "function_name": self.function_name,
            "message": self.message,
            "arguments": list(map(lambda a: a.serialize(), self.arguments)),
            "save_to": self.save_to,
            "block_type": BlockType.TRIGGER.value,
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


class VariableBlockArgument:
    def __init__(self):
        pass

    def serialize(self):
        return {"type": "variable"}


class DynamicBlockArgument:
    def __init__(self, type, callback):
        if type not in ALLOWED_ARGUMENT_TYPES:
            raise TypeError("Type “{}” not allowed".format(type))

        self.type = type
        self.callback = callback

    def serialize(self):
        return {
            "type": ALLOWED_ARGUMENT_TYPES[self.type],
            "values": {"callback": self.callback},
        }
