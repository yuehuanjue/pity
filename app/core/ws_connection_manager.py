# import abc
from typing import TypeVar

from fastapi import WebSocket

from app.utils.logger import Log

MsgType = TypeVar('MsgType', str, dict, bytes)


# class MsgSender(metaclass=abc.ABCMeta):
#     @abc.abstractmethod
#     def send_text(self):
#         pass
#
#     @abc.abstractmethod
#     def send_json(self):
#         pass
#
#     @abc.abstractmethod
#     def send_bytes(self):
#         pass


class ConnectionManager:
    def __init__(self):
        self.active_connections: dict[str, WebSocket] = {}
        self.log = Log("websocket")

    async def connect(self, websocket: WebSocket, client_id: str) -> None:
        await websocket.accept()
        exist: WebSocket = self.active_connections.get(client_id)
        if exist:
            await exist.close()
            self.active_connections[client_id]: WebSocket = websocket
        else:
            self.active_connections[client_id]: WebSocket = websocket
            self.log.info(F"websocket:{client_id}： 建立连接成功！")

    def disconnect(self, client_id: str) -> None:
        del self.active_connections[client_id]
        self.log.info(F"websocket:{client_id}： 已安全断开！")

    @staticmethod
    async def pusher(sender: WebSocket, message: MsgType) -> None:
        """
        根据不同的消息类型，调用不同方法发送消息
        """
        msg_mapping: dict = {
            str: sender.send_text,
            dict: sender.send_json,
            bytes: sender.send_bytes
        }
        if func_push_msg := msg_mapping.get(type(message)):
            await func_push_msg(message)
        else:
            raise TypeError(F"websocket不能发送{type(message)}的内容！")

    async def send_personal_message(self, message: MsgType, websocket: WebSocket) -> None:
        """
        发送个人信息
        """
        await self.pusher(sender=websocket, message=message)

    async def broadcast(self, message: MsgType) -> None:
        """
        广播
        """
        for connection in self.active_connections.values():
            await self.pusher(sender=connection, message=message)
