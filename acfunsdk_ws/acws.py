# coding=utf-8
import time
import random
import threading
import websocket
from .models.utils import ProtosMaker

__author__ = 'dolacmeo'


class AcWebSocket:
    ws_link = None
    config = None
    _main_thread = None
    tasks = dict()
    commands = dict()
    unread = []
    is_register_done = False
    is_close = True
    ws_recv_listener = None

    def __init__(self, acer, ws_links: list):
        self.acer = acer
        # websocket.enableTrace(True)
        self.ws_link = random.choice(ws_links)
        self.protos = ProtosMaker(self.acer, self.task)
        self.ws = websocket.WebSocketApp(
            url=self.ws_link,
            on_open=self._register,
            on_message=self._message,
            on_error=self._on_error,
            on_close=self._on_close,
            on_ping=self._keep_alive_request,
            on_pong=self._keep_alive_response,
        )
        self.listenner = dict()

    def run(self):
        def _run():
            self.ws.run_forever(
                ping_interval=10, ping_timeout=5,
                skip_utf8_validation=True,
                origin="live.acfun.cn",
            )
        self._main_thread = threading.Thread(target=_run)
        self._main_thread.start()
        self.is_close = False
        return self

    def add_task(self, seq_id: int, command, content):
        if self.is_close is True:
            return False
        if f"{seq_id}" not in self.tasks:
            self.tasks[f"{seq_id}"] = dict()
        self.tasks[f"{seq_id}"]["send"] = {"command": command, "content": content, "time": time.time()}
        if command not in self.commands:
            self.commands[command] = []
        self.commands[command].append({"seqId": f"{seq_id}", "way": "send", "time": time.time()})
        self.ws.send(content)

    def task(self, seq_id: int, command, content):
        self.add_task(seq_id, command, content)

    def ans_task(self, seq_id: int, command, result):
        if f"{seq_id}" not in self.tasks:
            self.tasks[f"{seq_id}"] = {}
        self.tasks[f"{seq_id}"]["recv"] = {"command": command, "content": result, "time": time.time()}
        if command not in self.commands:
            self.commands[command] = []
        self.commands[command].append({"seqId": f"{seq_id}", "way": "recv", "time": time.time()})
        if callable(self.ws_recv_listener):
            need_return = self.ws_recv_listener(seq_id, command, result)
            if need_return is True:
                return None
        else:
            self.unread.append(f"{seq_id}.recv")
        if command == 'Basic.Register':
            self.task(*self.protos.ClientConfigGet_Request())
            print(f"did       : {self.acer.did}")
            print(f"userId    : {self.acer.uid}")
            print(f"ssecurity : {self.acer.tokens['ssecurity']}")
            print(f"sessKey   : {self.acer.tokens['sessKey']}")
            self.is_register_done = True
            print(">>>>>>>> AcWebsocket Registed<<<<<<<<<")
        elif command == 'Basic.ClientConfigGet':
            self.task(*self.protos.KeepAlive_Request())
            self.protos.client_config = result
            print(">>>>>>>> AcWebsocket  Ready  <<<<<<<<<")
        elif command == 'Basic.KeepAlive':
            pass
        self.reader(seq_id, command, result)

    def reader(self, seq_id: int, command, result):
        print(f"{command=}")

    def _register(self, ws):
        print(">>>>>>> AcWebsocket Connecting<<<<<<<<")
        self.task(*self.protos.BasicRegister_Request())

    def _message(self, ws, message):
        self.ans_task(*self.protos.decode(message))

    def _keep_alive_request(self, ws, message):
        self.add_task(*self.protos.BasicPing_Request())

    def _keep_alive_response(self, ws, message):
        if self.is_register_done:
            self.add_task(*self.protos.KeepAlive_Request())

    def _on_close(self, ws, close_status_code, close_msg):
        # Because on_close was triggered, we know the opcode = 8
        if close_status_code or close_msg:
            print("on_close args:")
            print(f"  close status code: {close_status_code}")
            print(f"  close message    : {close_msg}")
        print(">>>>>>>> AcWebsocket  CLOSED <<<<<<<<<")

    def _on_error(self):
        # print("ERROR: ", e)
        self.close()

    def close(self):
        self.add_task(*self.protos.Unregister_Request())
        self.is_close = True
        self.ws.close()

    def restart(self):
        print(">>>>>>>> AcWebsocket  RESTART <<<<<<<<<")
        self.close()
        self.run()
