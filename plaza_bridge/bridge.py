import websocket
import logging
import json
import copy
import collections
import threading
import traceback

from .blocks import ServiceBlock, BlockType, CallbackBlockArgument
from . import protocol
from .service_configuration import ServiceConfiguration
from . import utils
from .extra_data import ExtraData

BlockEntry = collections.namedtuple('BlockEntry', ['block', 'function'])

class PlazaBridge:
    def __init__(self, name, endpoint=None, registerer=None, is_public=False):
        self.name = name
        self.endpoint = endpoint
        self.registerer = registerer
        self.is_public = is_public

        self.blocks = {}
        self.callbacks = {}
        self.callbacks_by_name = {}


    ## Decorators
    def getter(self,
               message,
               arguments=[],
               block_result_type=None,
               id=None,
    ):
        arguments = self._resolve_arguments(arguments)               
        
        def _decorator_getter(func):
            nonlocal id

            if id is None:
                id = func.__name__

            if id in self.blocks:
                raise Exception('A block with id "{}" already exists'.format(id))

            self.blocks[id] = BlockEntry(
                block=ServiceBlock(id=id,
                                   function_name=id,
                                   message="G " + message,
                                   block_type=BlockType.GETTER,
                                   block_result_type=utils.serialize_type(block_result_type),
                                   arguments=arguments,
                                   save_to=None),
                function=func)

            return func
        return _decorator_getter

    def callback(self, param=None):
        name = None
        def _decorator_callback(func):
            nonlocal name

            if name is None:
                name = func.__name__

            if name in self.callbacks_by_name:
                raise Exception('Callback with name "{}" already registered'.format(name))

            self.callbacks_by_name[name] = func
            self.callbacks[func] = (name, func)

            return func

        # If "param" is a function, the decorator was called with no `()`
        if callable(param):
            return _decorator_callback(param)
        else:
            name = param
            return _decorator_callback

    def operation(self,
                  message,
                  arguments=[],
                  save_to=None,
                  id=None,
    ):
        arguments = self._resolve_arguments(arguments)               

        def _decorator_operation(func):
            nonlocal id

            if id is None:
                id = func.__name__

            if id in self.blocks:
                raise Exception('A block with id "{}" already exists'.format(id))

            self.blocks[id] = BlockEntry(
                block=ServiceBlock(id=id,
                                   function_name=id,
                                   message="O "+ message,
                                   block_type=BlockType.OPERATION,
                                   block_result_type=None,
                                   arguments=arguments,
                                   save_to=save_to),
                function=func)

            return func
        return _decorator_operation

    ## Operation
    def run(self):
        if self.endpoint is None:
            raise Exception('No endpoint defined')

        self._run_loop()

    def _on_message(self, ws, message):
        assert(ws is self.websocket)
        logging.debug('Message on {}: {}'.format(ws, message))
        self._handle_message(message)

    def _on_open(self, ws):
        assert(ws is self.websocket)
        logging.debug('Connection opened on {}'.format(ws))

        ws.send(json.dumps(
            {"type": protocol.CONFIGURATION, "value": self.get_configuration().serialize()}
        ))

    def _on_error(self, ws, error):
        assert(ws is self.websocket)
        logging.debug('Error on {}: {}'.format(ws, error))

    def _on_close(self, ws):
        assert(ws is self.websocket)
        logging.debug('Connection closed on {}'.format(ws))
        
    def _run_loop(self):
        def _on_message(ws, msg): return self._on_message(ws, msg)
        def _on_error(ws, error): return self._on_error(ws, error)
        def _on_open(ws): return self._on_open(ws)
        def _on_close(ws): return self._on_close(ws)
        
        logging.debug('Connecting to {}'.format(self.endpoint))
        self.websocket = websocket.WebSocketApp(self.endpoint,
                                                on_message=_on_message,
                                                on_error=_on_error,
                                                on_open=_on_open,
                                                on_close=_on_close)
        self.websocket.run_forever()        

    ## Message handling
    def _handle_message(self, message):
        (msg_type, value, message_id, extra_data) = self._parse(message)

        if msg_type == protocol.CALL_MESSAGE_TYPE:
            self._handle_call(value, message_id, extra_data)

        elif msg_type == protocol.GET_HOW_TO_SERVICE_REGISTRATION:
            self._handle_get_service_registration(value, message_id, extra_data)

        elif msg_type == protocol.REGISTRATION_MESSAGE:
            self._handle_registration(value, message_id, extra_data)

        elif msg_type == protocol.OAUTH_RETURN:
            self._handle_oauth_return(value, message_id, extra_data)

        elif msg_type == protocol.DATA_CALLBACK:
            self._handle_data_callback(value, message_id, extra_data)

        else:
            raise Exception("Unknown message type “{}”".format(msg_type))

    def _handle_call(self, value, message_id, extra_data):
        function_name = value["function_name"]
        def _handling():
            try:
                func = self.blocks[function_name].function
                response = func(
                    *value["arguments"], extra_data
                )
            except:
                logging.error(traceback.format_exc())
                self.websocket.send(
                    json.dumps({"message_id": message_id, "success": False})
                )
                return
    
            self.websocket.send(
                json.dumps(
                    {
                        "message_id": message_id,
                        "success": True,
                        "result": response,
                    }
                )
            )
        self._run_parallel(_handling)

    def _handle_get_service_registration(self, value, message_id, extra_data):
            if self.registerer is None:
                self.websocket.send(
                    json.dumps(
                        {"message_id": message_id, "success": True, "result": None}
                    )
                )
            else:
                def _handling():
                    self.websocket.send(
                        json.dumps(
                            {
                                "message_id": message_id,
                                "success": True,
                                "result": self.registerer.serialize(extra_data),
                            }
                        )
                    )
                self._run_parallel(_handling)

    def _handle_registration(self, value, message_id, extra_data):
        if self.registerer is None:
            self.websocket.send(
                json.dumps(
                    {
                        "message_id": message_id,
                        "success": False,
                        "error": "No registerer available",
                    }
                )
            )
        else:
            def _handling():
                try:
                    result = self.registerer.register(value, extra_data)
                except:
                    logging.error(traceback.format_exc())
                    self.websocket.send(
                        json.dumps({"message_id": message_id, "success": False})
                    )
                    return

                message = None
                if result != True:
                    result, message = result
    
                self.websocket.send(
                    json.dumps(
                        {
                            "message_id": message_id,
                            "success": result,
                            "message": message,
                        }
                    )
                )
            self._run_parallel(_handling)

    def _handle_oauth_return(self, value, message_id, extra_data):
        if self.registerer is None:
            self.websocket.send(
                json.dumps(
                    {
                        "message_id": message_id,
                        "success": False,
                        "error": "No registerer available",
                    }
                )
            )
        else:
            def _handling():
                result = self.registerer.register(value, extra_data)
                message = None
                if result != True:
                    result, message = result
    
                self.websocket.send(
                    json.dumps(
                        {
                            "message_id": message_id,
                            "success": result,
                            "message": message,
                        }
                    )
                )
            self._run_parallel(_handling)


    def _handle_data_callback(self, value, message_id, extra_data):
        def _handling():
            try:
                response = self.callbacks_by_name[value["callback"]](extra_data)
            except:
                logging.warn(traceback.format_exc())
                self.websocket.send(
                    json.dumps({"message_id": message_id, "success": False})
                )
                return

            self.websocket.send(
                json.dumps(
                    {"message_id": message_id, "success": True, "result": response}
                )
            )
        self._run_parallel(_handling)


    ## Auxiliary
    def get_configuration(self):
        blocks = [block.block for block in self.blocks.values()]
      
        return ServiceConfiguration(service_name=self.name,
                                    is_public=self.is_public,
                                    registration=self.registerer,
                                    blocks=blocks)

    def _resolve_arguments(self, arguments):
        # Resolve callbacks
        for arg in arguments:
            if isinstance(arg, CallbackBlockArgument):
                if callable(arg.callback): # A function, so a callback
                    arg.callback = self.callbacks[arg.callback][0]

        return arguments

    def _parse(self, message):
        parsed = json.loads(message)
        return (
            parsed["type"],
            parsed["value"],
            parsed["message_id"],
            ExtraData(parsed.get("user_id"), parsed.get("extra_data", None)),
        )

    def _run_parallel(self, func):
        threading.Thread(target=func).start()
