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
        save_to=None,
    ):
        self.id = id
        self.function_name = function_name
        self.message = message
        self.block_type = block_type
        self.block_result_type = block_result_type
        self.arguments = arguments
        self.save_to = save_to

    def serialize(self):
        return {
            "id": self.id,
            "function_name": self.function_name,
            "message": self.message,
            "arguments": list(map(lambda a: a.serialize(), self.arguments)),
            "block_type": self.block_type.value,
            "block_result_type": self.block_result_type,
            "save_to": self.save_to,
        }


class ServiceTriggerBlock:
    def __init__(
        self,
        id,
        function_name,
        message,
        arguments=[],
        save_to=None,
        expected_value=None,
        key=None,
        subkey=None,
    ):
        self.id = id
        self.function_name = function_name
        self.message = message
        self.arguments = arguments
        self.save_to = save_to
        self.expected_value = expected_value
        if key is not None:
            self.key = key
        else:
            self.key = function_name
        self.subkey = subkey

    def serialize(self):
        return {
            "id": self.id,
            "function_name": self.function_name,
            "message": self.message,
            "arguments": list(map(lambda a: a.serialize(), self.arguments)),
            "save_to": self.save_to,
            "expected_value": self.expected_value,
            "block_type": BlockType.TRIGGER.value,
            "key": self.key,
            "subkey": self.subkey,
        }


ALLOWED_ARGUMENT_TYPES = {
    str: "string",
    int: "integer",
    float: "float",
    bool: "boolean",
}


SINGLE_VARIABLE_CLASS = "single"
LIST_VARIABLE_CLASS = "list"

ALLOWED_VARIABLE_CLASSES = {
    list: LIST_VARIABLE_CLASS,
    str: SINGLE_VARIABLE_CLASS,
    int: SINGLE_VARIABLE_CLASS,
    float: SINGLE_VARIABLE_CLASS,
    bool: SINGLE_VARIABLE_CLASS,
    None: SINGLE_VARIABLE_CLASS,
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
    def __init__(self, _class=None):
        if _class not in ALLOWED_VARIABLE_CLASSES:
            raise TypeError("Variable class “{}” not allowed".format(_class))
        self.variable_class = ALLOWED_VARIABLE_CLASSES[_class]

    def serialize(self):
        return {"type": "variable", "class": self.variable_class}


class CallbackBlockArgument:
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
