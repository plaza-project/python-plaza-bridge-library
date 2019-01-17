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

    def __parse(self, message):
        parsed = json.loads(message)
        return (parsed['type'], parsed['value'], parsed['message_id'])


    async def __interact(self, websocket):
        async for message in websocket:
            logging.debug("Received: {}".format(message))
            (msg_type, value, message_id) = self.__parse(message)

            if msg_type == protocol.CALL_MESSAGE_TYPE:
                if value['function_name'] == '__ping':
                    await websocket.send(json.dumps({
                        'message_id': message_id,
                        'success': True,
                        'result': 'PONG',
                    }))
                else:
                    self.handle_call(value['function_name'], value['arguments'])

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