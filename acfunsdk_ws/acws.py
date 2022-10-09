# coding=utf-8
import time
import random
import threading
import websocket
from .models.utils import ProtosMaker

__author__ = 'dolacmeo'


class AcWebSocket:
    ws_link = None
    _main_thread = None
    tasks = dict()
    commands = dict()
    is_register_done = False
    is_close = True

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

    def task(self, seq_id: int, command, content):
        if self.is_close is True:
            return False
        if f"{seq_id}" not in self.tasks:
            self.tasks[f"{seq_id}"] = dict()
        self.tasks[f"{seq_id}"]["send"] = {"command": command, "content": content, "time": time.time()}
        if command not in self.commands:
            self.commands[command] = []
        self.commands[command].append({"seqId": f"{seq_id}", "way": "send", "time": time.time()})
        self.ws.send(content)

    def ans_task(self, seq_id: int, command, result):
        if command == 'Basic.Register':
            self.task(*self.protos.ClientConfigGet_Request())
            self.is_register_done = True
        elif command == 'Basic.ClientConfigGet':
            self.task(*self.protos.KeepAlive_Request())
            self.protos.client_config = result
        elif command == 'Basic.KeepAlive':
            pass
        self.reader(seq_id, command, result)

    def reader(self, seq_id: int, command, result):
        print(f"{command=}")

    def _register(self, ws):
        self.task(*self.protos.BasicRegister_Request())

    def _message(self, ws, message):
        self.ans_task(*self.protos.decode(message))

    def _keep_alive_request(self, ws, message):
        self.task(*self.protos.BasicPing_Request())

    def _keep_alive_response(self, ws, message):
        if self.is_register_done:
            self.task(*self.protos.KeepAlive_Request())

    def _on_close(self, ws, close_status_code, close_msg):
        # Because on_close was triggered, we know the opcode = 8
        # if close_status_code or close_msg:
        #     print("on_close args:")
        #     print(f"  close status code: {close_status_code}")
        #     print(f"  close message    : {close_msg}")
        # print(">>>>>>>> AcWebsocket  CLOSED <<<<<<<<<")
        pass

    def _on_error(self):
        # print(f"ONERROR: {e=}")
        self.close()

    def close(self):
        self.task(*self.protos.Unregister_Request())
        self.is_close = True
        self.ws.close()

    def restart(self):
        self.close()
        self.run()
