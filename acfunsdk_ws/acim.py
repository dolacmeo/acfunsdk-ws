# coding=utf-8
from .acws import AcWebSocket

__author__ = 'dolacmeo'


class AcIM(AcWebSocket):

    def __init__(self, acer, ws_links: [list, None] = None):
        super().__init__(acer, ws_links)

    def reader(self, seq_id: int, command, result):
        pass

    def im_get_sessions(self):
        message = self.protos.MessageSession_Request()
        return self.task(*message)

    def im_session_start(self, uid: int):
        message = self.protos.SessionCreate_Request(uid)
        return self.task(*message)

    def im_session_close(self, uid: int):
        message = self.protos.SessionRemove_Request(uid)
        return self.task(*message)

    def im_pull_message(self, uid: int, minSeq: int, maxSeq: int, count: int = 10):
        message = self.protos.MessagePullOld_Request(uid, minSeq, maxSeq, count)
        return self.task(*message)

    def im_send(self, uid: int, content: str):
        message = self.protos.MessageContent_Request(uid, content)
        return self.task(*message)

    def im_send_image(self, uid: int, image_data: bytes):
        message = self.protos.MessageImage_Request(uid, image_data)
        return self.task(*message)
