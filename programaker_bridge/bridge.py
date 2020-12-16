import base64
import collections
import json
import logging
import os
import re
import string
import threading
import traceback
import urllib.parse
import uuid

import websocket

from . import protocol, utils
from .blocks import BlockType, CallbackBlockArgument, ServiceBlock, ServiceTriggerBlock
from .extra_data import ExtraData
from .service_configuration import ServiceConfiguration

BlockEntry = collections.namedtuple("BlockEntry", ["block", "function"])

PING_INTERVAL = 30  # Ping every 30 seconds, usually disconnections are at 60s
ALLOWED_EVENT_CHARS = string.ascii_lowercase + "_"
ALLOWED_COLLECTION_CHARS = ALLOWED_EVENT_CHARS
DEDUPLICATE_UNDERSCORE_RE = re.compile("__+")


def message_to_id(message):
    sanitized = "".join(
        [chr if chr in ALLOWED_EVENT_CHARS else "_" for chr in message.lower()]
    )
    return DEDUPLICATE_UNDERSCORE_RE.sub("_", sanitized).strip("_")


class Event:
    def __init__(self, manager, name):
        self._manager = manager
        self._name = name
        self._on_new_listeners = None

    def add_trigger_block(
        self,
        message,
        arguments=[],
        save_to=None,
        id=None,
        expected_value=None,
        subkey=None,
    ):
        if id is None:
            id = self._name + "_" + message_to_id(message)

        block = ServiceTriggerBlock(
            id=id,
            function_name=id,
            message=message,
            arguments=arguments,
            save_to=save_to,
            expected_value=expected_value,
            key=self._name,
            subkey=subkey,
        )
        self._manager._add_trigger_block(block)

    def on_new_listeners(self, func):
        if self._on_new_listeners is not None:
            raise Exception(
                '"on_new_listeners" registry already defined: "{}"'.format(
                    self._on_new_listeners
                )
            )

        self._on_new_listeners = func
        return func

    def trigger_on_new_listeners(self, user_id, subkey):
        func = self._on_new_listeners
        return func(user_id, subkey)

    def send(self, content, event=None, to_user=None, subkey=None):
        if event is None:
            event = content

        self._manager._send_raw(
            json.dumps(
                {
                    "type": protocol.NOTIFICATION,
                    "key": self._name,
                    "subkey": subkey,
                    "to_user": to_user,
                    "value": event,
                    "content": content,
                }
            )
        )


class EventManager:
    def __init__(self, bridge, event_names):

        if any(
            [
                name.startswith("_")
                or not all([char in ALLOWED_EVENT_CHARS for char in name])
                for name in event_names
            ]
        ):
            raise Exception(
                "Names can only contain characters '{}'".format(ALLOWED_EVENT_CHARS)
            )

        self._bridge = bridge
        self._events = {event: Event(self, event) for event in event_names}

    def __getattr__(self, event_name):
        if event_name not in self._events:
            raise AttributeError('No event named "{}"'.format(event_name))

        return self._events[event_name]

    def _add_trigger_block(self, block):
        self._bridge._add_trigger_block(block)

    def _send_raw(self, data):
        self._bridge._send_raw(data)


class ManagedCollection:
    def __init__(self, manager, name):
        self.manager = manager
        self.name = name
        self.callback = None

    def getter(self, param=None):
        def _decorator_callback(func):
            if self.callback is not None:
                raise Exception(
                    "{} collection's callback already registered".format(self.name)
                )

            self.callback = func
            self.manager._bridge._add_callback_with_name(self.name, self._callback)
            return func

        # If "param" is a function, the decorator was called with no `()`
        if callable(param):
            return _decorator_callback(param)
        else:
            return _decorator_callback

    def _callback(self, extra_data):
        return self.callback(extra_data.user_id, extra_data)


class CollectionManager:
    def __init__(self, bridge, collections):
        if any(
            [
                name.startswith("_")
                or not all([char in ALLOWED_EVENT_CHARS for char in name])
                for name in collections
            ]
        ):
            raise Exception(
                "Names can only contain characters '{}'".format(
                    ALLOWED_COLLECTION_CHARS
                )
            )

        self._bridge = bridge
        self._collections = {
            collection: ManagedCollection(self, collection)
            for collection in collections
        }

    def __getattr__(self, collection_name):
        if collection_name not in self._collections:
            raise AttributeError('No collection named "{}"'.format(collection_name))

        return self._collections[collection_name]


class ProgramakerBridge:
    def __init__(
        self,
        name,
        endpoint=None,
        token=None,
        registerer=None,
        is_public=False,
        events=[],
        collections=[],
        icon=None,
        allow_multiple_connections=False,
    ):
        self.name = name
        self.endpoint = endpoint
        self.token = token
        self.registerer = registerer
        self.is_public = is_public
        self.icon = icon
        self.allow_multiple_connections = allow_multiple_connections
        self._sent_messages = {}
        self._ready_triggered = False

        self.blocks = {}
        self.callbacks = {}
        self.callbacks_by_name = {}
        self.events = EventManager(self, events)
        self.collections = CollectionManager(self, collections)
        self.on_ready = None

    ## Decorators
    def getter(self, id, message, arguments=[], block_result_type=None):
        arguments = self._resolve_arguments(arguments)

        def _decorator_getter(func):
            nonlocal id

            if id in self.blocks:
                raise Exception('A block with id "{}" already exists'.format(id))

            self.blocks[id] = BlockEntry(
                block=ServiceBlock(
                    id=id,
                    function_name=id,
                    message=message,
                    block_type=BlockType.GETTER,
                    block_result_type=utils.serialize_type(block_result_type),
                    arguments=arguments,
                    save_to=None,
                ),
                function=func,
            )

            return func

        return _decorator_getter

    def callback(self, param=None):
        name = None

        def _decorator_callback(func):
            nonlocal name

            if name is None:
                name = func.__name__

            self._add_callback_with_name(name, func)

            return func

        # If "param" is a function, the decorator was called with no `()`
        if callable(param):
            return _decorator_callback(param)
        else:
            name = param
            return _decorator_callback

    def operation(self, id, message, arguments=[], save_to=None):
        arguments = self._resolve_arguments(arguments)

        def _decorator_operation(func):
            nonlocal id

            if id in self.blocks:
                raise Exception('A block with id "{}" already exists'.format(id))

            self.blocks[id] = BlockEntry(
                block=ServiceBlock(
                    id=id,
                    function_name=id,
                    message=message,
                    block_type=BlockType.OPERATION,
                    block_result_type=None,
                    arguments=arguments,
                    save_to=save_to,
                ),
                function=func,
            )

            return func

        return _decorator_operation

    def get_oauth_return_url(self):
        parsed = urllib.parse.urlparse(self.endpoint)

        if parsed.scheme == "ws":
            proto = "http"
        elif parsed.scheme == "wss":
            proto = "https"
        else:
            proto = parsed.scheme

        if ":" in parsed.netloc:
            host, port_num = parsed.netloc.split(":", 1)
            port = ":" + port_num
        else:
            host = parsed.netloc
            port = ""

        bridge_id = parsed.path.rstrip("/").split("/")[-2]

        return_uri = (
            f"{proto}://{host}{port}/api/v0/bridges/by-id/{bridge_id}/oauth_return"
        )
        return return_uri

    ## External block additions
    def _add_trigger_block(self, block):
        self.blocks[block.id] = BlockEntry(block, None)

    def _add_callback_with_name(self, name, func):
        if name in self.callbacks_by_name:
            raise Exception('Callback with name "{}" already registered'.format(name))

        self.callbacks_by_name[name] = func
        self.callbacks[func] = (name, func)

    ## Operation
    def run(self):
        if self.endpoint is None:
            raise Exception("No endpoint defined")

        self._run_loop()

    def establish_connection(self, connection_id, name=None):
        self._send_raw(
            json.dumps(
                {
                    "type": protocol.ESTABLISH_CONNECTION,
                    "value": {
                        "connection_id": connection_id,
                        "name": name,
                    },
                }
            )
        )

    ## Internal callbacks
    def _on_message(self, ws, message):
        assert ws is self.websocket
        logging.debug("Message on {}: {}".format(ws, message))
        try:
            self._handle_message(message)
        except:
            logging.error(
                "Error message [{}]: {}".format(message, traceback.format_exc())
            )

    def _on_open(self, ws):
        assert ws is self.websocket
        logging.debug("Connection opened on {}".format(ws))

        if self.token is not None:
            ws.send(
                json.dumps(
                    {"type": protocol.AUTHENTICATION, "value": {"token": self.token}}
                )
            )

        ws.send(
            json.dumps(
                {
                    "type": protocol.CONFIGURATION,
                    "value": self.get_configuration().serialize(),
                }
            )
        )
        self._send_advice()
        if self.on_ready is not None and not self._ready_triggered:
            logging.debug("Triggering on_ready: {}".format(self.on_ready))
            self.on_ready()
        self._ready_triggered = True

    def _send_advice(self):
        self._send_notify_listeners_advice()

    def _send_notify_listeners_advice(self):
        listen_notify_channels = []
        for _event_id, event in self.events._events.items():
            if event._on_new_listeners is not None:  # Listening event set
                listen_notify_channels.append(event._name)

        if len(listen_notify_channels) > 0:
            mid = str(uuid.uuid4())
            self.websocket.send(
                json.dumps(
                    {
                        "type": protocol.ADVICE,
                        "message_id": mid,
                        "value": {"NOTIFY_SIGNAL_LISTENERS": listen_notify_channels},
                    }
                )
            )
            self._sent_messages[mid] = (
                ("ADVICE", "NOTIFY_SIGNAL_LISTENERS"),
                listen_notify_channels,
            )

    def _on_error(self, ws, error):
        assert ws is self.websocket
        logging.error("Error on {}: {}".format(ws, error))

    def _on_close(self, ws):
        assert ws is self.websocket
        logging.warn("Connection closed on {}".format(ws))

    def _run_loop(self):
        def _on_message(ws, msg):
            return self._on_message(ws, msg)

        def _on_error(ws, error):
            return self._on_error(ws, error)

        def _on_open(ws):
            return self._on_open(ws)

        def _on_close(ws):
            return self._on_close(ws)

        logging.debug("Connecting to {}".format(self.endpoint))
        self.websocket = websocket.WebSocketApp(
            self.endpoint,
            on_message=_on_message,
            on_error=_on_error,
            on_open=_on_open,
            on_close=_on_close,
        )
        self.websocket.run_forever(ping_interval=PING_INTERVAL)

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

        elif message_id in self._sent_messages:
            del self._sent_messages[message_id]  # @TODO Use the result

        elif msg_type == protocol.ADVICE_NOTIFICATION:
            self._handle_advice(value, message_id, extra_data)

        elif msg_type == protocol.ICON_REQUEST:
            self._handle_icon_request(value, message_id, extra_data)

        else:
            raise Exception("Unknown message type “{}”".format(msg_type))

    def _handle_call(self, value, message_id, extra_data):
        function_name = value["function_name"]

        def _handling():
            try:
                func = self.blocks[function_name].function
                response = func(*value["arguments"], extra_data)
            except:
                logging.error(traceback.format_exc())
                self._send_raw(json.dumps({"message_id": message_id, "success": False}))
                return

            self._send_raw(
                json.dumps(
                    {"message_id": message_id, "success": True, "result": response}
                )
            )

        self._run_parallel(_handling)

    def _handle_get_service_registration(self, value, message_id, extra_data):
        if self.registerer is None:
            self._send_raw(
                json.dumps({"message_id": message_id, "success": True, "result": None})
            )
        else:

            def _handling():
                self._send_raw(
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
            # If no registration is needed, connection is always established
            self._send_raw(
                json.dumps(
                    {
                        "message_id": message_id,
                        "success": True,
                    }
                )
            )
        else:

            def _handling():
                try:
                    result = self.registerer.register(value, extra_data)
                except:
                    logging.error(traceback.format_exc())
                    self._send_raw(
                        json.dumps({"message_id": message_id, "success": False})
                    )
                    return

                data = {}
                if result != True:
                    result, data = result

                if not isinstance(data, dict) or not "name" in data:
                    logging.warning(
                        "Note it's preferrable to set the return value of a register() call to"
                        " (True, {'name': <connection_name>})."
                        " This is *required* for multiple connections on a single user."
                    )

                self._send_raw(
                    json.dumps(
                        {
                            "message_id": message_id,
                            "success": result,
                            "data": data,
                        }
                    )
                )

            self._run_parallel(_handling)

    def _handle_oauth_return(self, value, message_id, extra_data):
        if self.registerer is None:
            self._send_raw(
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
                    result = False

                message = None
                if result not in (True, False):
                    result, message = result

                self._send_raw(
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
                self._send_raw(json.dumps({"message_id": message_id, "success": False}))
                return

            self._send_raw(
                json.dumps(
                    {"message_id": message_id, "success": True, "result": response}
                )
            )

        self._run_parallel(_handling)

    def _handle_advice(self, value, message_id, extra_data):
        for advice in value:
            if advice == "SIGNAL_LISTENERS":
                self._handle_signal_listeners_update(
                    value[advice], message_id, extra_data
                )
            else:
                logging.info(
                    "Received unhandled ADVICE_NOTIFICATION (this will not be a problem)."
                )

    def _handle_icon_request(self, _value, _message_id, _extra_data):
        if not self.icon or not "read" in dir(self.icon):
            logging.error("Requested icon. Cannot be read")
            return

        data = base64.b64encode(self.icon.read()).decode("utf-8")
        self._send_raw(
            json.dumps({"type": protocol.ICON_UPLOAD, "value": {"content": data}})
        )

    def _handle_signal_listeners_update(self, update, message_id, extra_data):
        logging.info("Update: {}".format(update))
        for user, listeners in update.items():
            for event_ref in listeners:
                matching_events = self._find_matching_events(event_ref)
                for event in matching_events:
                    if event._on_new_listeners is not None:
                        if isinstance(event_ref, dict):
                            event.trigger_on_new_listeners(
                                user, event_ref.get("subkey", None)
                            )
                        else:
                            event.trigger_on_new_listeners(user, event_ref)

    def _find_matching_events(self, event_ref):
        results = []
        for event in self.events._events.values():
            if self._is_match_event_ref(event, event_ref):
                results.append(event)
        return results

    def _is_match_event_ref(self, event, event_ref):
        if event_ref == "__all__":
            return True

        return event_ref.get("key", None) == event._name

    ## Auxiliary
    def _send_raw(self, data):
        self.websocket.send(data)

    def get_configuration(self):
        blocks = [block.block for block in self.blocks.values()]

        return ServiceConfiguration(
            service_name=self.name,
            is_public=self.is_public,
            registration=self.registerer,
            blocks=blocks,
            icon=self.icon,
            allow_multiple_connections=self.allow_multiple_connections,
            collection_manager=self.collections,
        )

    def _resolve_arguments(self, arguments):
        # Resolve callbacks
        for arg in arguments:
            if isinstance(arg, CallbackBlockArgument):
                if callable(arg.callback):  # A function, so a callback
                    arg.callback = self.callbacks[arg.callback][0]

        return arguments

    def _parse(self, message):
        parsed = json.loads(message)
        return (
            parsed.get("type"),
            parsed.get("value"),
            parsed.get("message_id"),
            ExtraData(parsed.get("user_id"), parsed.get("extra_data", None)),
        )

    def _run_parallel(self, func):
        threading.Thread(target=func).start()
