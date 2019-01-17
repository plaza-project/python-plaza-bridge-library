import asyncio
import websockets
import json
import logging
import traceback
import time

from . import protocol

SLEEP_BETWEEN_RETRIES = 5


class AnswerHandler:
    def __init__(self, message_id, websocket):
        self.message_id = message_id
        self.websocket = websocket


class PlazaService:
    def __init__(self, service_url):
        self.service_url = service_url
        self.INTERNAL_FUNCTION_NAMES = {
            '__ping': self.__answer_ping
       }

    async def __answer_ping(self, websocket, message):
        (_msg_type, _value, message_id) = message
        await websocket.send(json.dumps({
                'message_id': message_id,
                'success': True,
                'result': 'PONG',
        }))

    def __parse(self, message):
        parsed = json.loads(message)
        return (parsed['type'], parsed['value'], parsed['message_id'])


    async def __interact(self, websocket):
        async for message in websocket:
            logging.debug("Received: {}".format(message))
            (msg_type, value, message_id) = self.__parse(message)

            if msg_type == protocol.CALL_MESSAGE_TYPE:
                function_name = value['function_name']

                if function_name in self.INTERNAL_FUNCTION_NAMES:
                    await self.INTERNAL_FUNCTION_NAMES[function_name](websocket, (msg_type, value, message_id))
                else:
                    try:
                        response = self.handle_call(function_name, value['arguments'])
                    except:
                        logging.warn(traceback.format_exc())
                        await websocket.send(json.dumps({
                            'message_id': message_id,
                            'success': False,
                        }))
                        continue

                    await websocket.send(json.dumps({
                        'message_id': message_id,
                        'success': True,
                        'result': response
                    }))

            else:
                raise Exception('Unknown message type on ({})'.format(message))

    async def __connect(self):
        async with websockets.connect(self.service_url) as websocket:
            logging.debug('Connected')
            await self.__interact(websocket)

    def run(self):
        while True:
            try:
                asyncio.get_event_loop().run_until_complete(
                    self.__connect())
            except KeyboardInterrupt:
                return
            except:
                logging.warn(traceback.format_exc())

            logging.debug("Waiting {} for reconnection".format(SLEEP_BETWEEN_RETRIES))
            time.sleep(SLEEP_BETWEEN_RETRIES)
            logging.debug("Reconnecting")