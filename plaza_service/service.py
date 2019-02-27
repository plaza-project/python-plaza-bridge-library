import asyncio
import websockets
import json
import logging
import traceback
import time

from . import protocol
from .service_configuration import ServiceConfiguration

SLEEP_BETWEEN_RETRIES = 5

class ExtraData:
    def __init__(self, user_id):
        self.user_id = user_id

class AnswerHandler:
    def __init__(self, message_id, websocket):
        self.message_id = message_id
        self.websocket = websocket


class PlazaService:
    def __init__(self, service_url):
        self.service_url = service_url
        self.INTERNAL_FUNCTION_NAMES = {"__ping": self.__answer_ping}
        self.__registerer = None

    async def __answer_ping(self, websocket, message):
        (_msg_type, _value, message_id) = message
        await websocket.send(
            json.dumps({"message_id": message_id, "success": True, "result": "PONG"})
        )

    def __parse(self, message):
        parsed = json.loads(message)
        return (parsed["type"], parsed["value"], parsed["message_id"], ExtraData(parsed.get("user_id")))

    async def __interact(self, websocket):
        async for message in websocket:
            logging.debug("Received: {}".format(message))
            (msg_type, value, message_id, extra_data) = self.__parse(message)

            if msg_type == protocol.CALL_MESSAGE_TYPE:
                function_name = value["function_name"]

                if function_name in self.INTERNAL_FUNCTION_NAMES:
                    await self.INTERNAL_FUNCTION_NAMES[function_name](
                        websocket, (msg_type, value, message_id), extra_data
                    )
                else:
                    try:
                        response = await self.handle_call(function_name, value["arguments"], extra_data)
                    except:
                        logging.warn(traceback.format_exc())
                        await websocket.send(
                            json.dumps({"message_id": message_id, "success": False})
                        )
                        continue

                    await websocket.send(
                        json.dumps(
                            {
                                "message_id": message_id,
                                "success": True,
                                "result": response,
                            }
                        )
                    )

            elif msg_type == protocol.GET_HOW_TO_SERVICE_REGISTRATION:
                if self.__registerer is None:
                    await websocket.send(
                        json.dumps(
                            {
                                "message_id": message_id,
                                "success": True,
                                "result": None,
                            }
                        )
                    )
                else:
                    await websocket.send(
                        json.dumps(
                            {
                                "message_id": message_id,
                                "success": True,
                                "result": self.__registerer.serialize(extra_data),
                            }
                        )
                    )

            elif msg_type == protocol.REGISTRATION_MESSAGE:
                if self.__registerer is None:
                    await websocket.send(
                        json.dumps(
                            {
                                "message_id": message_id,
                                "success": False,
                                "error": "No registerer available",
                            }
                        )
                    )
                else:
                    result = await self.__registerer.register(value, extra_data)
                    message = None
                    if result != True:
                        result, message = result

                    await websocket.send(
                        json.dumps(
                            {
                                "message_id": message_id,
                                "success": result,
                                "message": message,
                            }
                        )
                    )

            elif msg_type == protocol.OAUTH_RETURN:
                if self.__registerer is None:
                    await websocket.send(
                        json.dumps(
                            {
                                "message_id": message_id,
                                "success": False,
                                "error": "No registerer available",
                            }
                        )
                    )
                else:
                    result = await self.__registerer.register(value, extra_data)
                    message = None
                    if result != True:
                        result, message = result

                    await websocket.send(
                        json.dumps(
                            {
                                "message_id": message_id,
                                "success": result,
                                "message": message,
                            }
                        )
                    )

            elif msg_type == protocol.DATA_CALLBACK:
                try:
                    response = await self.handle_data_callback(value['callback'], extra_data)
                except:
                    logging.warn(traceback.format_exc())
                    await websocket.send(
                        json.dumps({"message_id": message_id, "success": False})
                    )
                    continue

                await websocket.send(
                    json.dumps(
                        {
                            "message_id": message_id,
                            "success": True,
                            "result": response,
                        }
                    )
                )

            else:
                raise Exception("Unknown message type “{}”".format(msg_type))

    async def __connect(self):
        async with websockets.connect(self.service_url) as websocket:
            logging.info("Connected successfully")
            configuration = self.handle_configuration()
            self.__registerer = configuration.registration
            if not isinstance(configuration, ServiceConfiguration):
                raise TypeError(
                    "Configuration has to inherit plaza_service.ServiceConfiguration"
                )

            logging.debug(
                "Setting configuration: {}".format(
                    json.dumps(configuration.serialize(), indent=4)
                )
            )

            await websocket.send(
                json.dumps(
                    {"type": "configuration", "value": configuration.serialize()}
                )
            )

            await self.__interact(websocket)

    def run(self):
        while True:
            try:
                asyncio.get_event_loop().run_until_complete(self.__connect())
            except KeyboardInterrupt:
                return
            except:
                logging.warn(traceback.format_exc())

            logging.debug("Waiting {}s for reconnection".format(SLEEP_BETWEEN_RETRIES))
            time.sleep(SLEEP_BETWEEN_RETRIES)
            logging.debug("Reconnecting")

