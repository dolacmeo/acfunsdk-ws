# coding=utf-8
import os
import json
import time
import random
import psutil
import threading
import websocket
import subprocess
from models import AcProtos
from utils import ac_live_room_reader

__author__ = 'dolacmeo'


class AcWebSocket:
    appId = 0
    instanceId = 0
    ws_link = None
    config = None
    _main_thread = None
    tasks = dict()
    commands = dict()
    unread = []
    is_register_done = False
    live_room = None
    player_config = None
    live_room_msg_bans = []
    live_room_gift = None
    live_obj = None
    live_log = None
    _live_player = None
    is_close = True
    ws_recv_listener = None

    def __init__(self, acer, ws_links: list):
        self.acer = acer
        # websocket.enableTrace(True)
        self.ws_link = random.choice(ws_links)
        self.protos = AcProtos(self)
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
        if self.live_log is not None:
            self.live_log.write(json.dumps({
                "command": command,
                "message": result,
                "time": time.time(),
                "seqId": f"{seq_id}"
            }, separators=(',', ':')))
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
            # print(f"did       : {self.acer.did}")
            # print(f"userId    : {self.acer.uid}")
            # print(f"ssecurity : {self.acer.tokens['ssecurity']}")
            # print(f"sessKey   : {self.acer.tokens['sessKey']}")
            self.is_register_done = True
            # print(">>>>>>>> AcWebsocket Registed<<<<<<<<<")
        elif command == 'Basic.ClientConfigGet':
            self.task(*self.protos.KeepAlive_Request())
            self.protos.client_config = result
            # print(">>>>>>>> AcWebsocket  Ready  <<<<<<<<<")
        elif command == 'LiveCmd.ZtLiveCsEnterRoomAck':
            self.live_room = self.protos.live_room
            self.live_room_gift = self.live_obj.gift_list()
            self.task(*self.protos.ZtLiveCsHeartbeat_Request())
            self.task(*self.protos.ZtLiveInteractiveMessage_Request())
            # print(">>>>>>>> AcWebsocket EnterRoom <<<<<<<<")
            # live_data = json.loads(self.live_room.get('videoPlayRes', "")).get('liveAdaptiveManifest', [])[0]
            # live_adapt = live_data.get('adaptationSet', {}).get('representation', {})
            # if self.player_config is None:
            #     print(f"未设置PotPlayer 请使用串流地址 请自行播放 \r\n {live_adapt[2]['url']}")
            # else:
            #     create_time = self.live_room.get('liveStartTime', 0) // 1000
            #     start_time = time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(create_time))
            #     live_up_name = self.live_obj.username
            #     live_type = self.live_obj.raw.get("type", {})
            #     live_title = " ".join([
            #         f"AcLive(#{self.live_obj.uid} @{live_up_name}| {live_type['categoryName']}>>{live_type['name']})",
            #         self.live_room['caption'], f"🎬 {start_time}"
            #     ])
            #     potplayer = self.player_config['player_path']
            #     # print(f"[{potplayer}] 开始播放......\r\n {live_title}")
            #     live_obs_stream = live_adapt[self.player_config['quality']]['url']
            #     cmd_list = [potplayer, live_obs_stream, "/title", f'"{live_title}"']
            #     self._live_player = subprocess.Popen(cmd_list, creationflags=subprocess.CREATE_NO_WINDOW)
        if command.startswith("LivePush.") and result:
            msg = ac_live_room_reader(result, self.live_room_gift, self.live_room_msg_bans)
            for n in msg:
                print(n)

    def _register(self, ws):
        # print(">>>>>>> AcWebsocket Connecting<<<<<<<<")
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
        # if close_status_code or close_msg:
        #     print("on_close args:")
        #     print(f"  close status code: {close_status_code}")
        #     print(f"  close message    : {close_msg}")
        print(">>>>>>>> AcWebsocket  CLOSED <<<<<<<<<")

    def _on_error(self, ws, e):
        print("ERROR: ", e)
        self.close()

    def close(self):
        self.add_task(*self.protos.Unregister_Request())
        self.is_close = True
        if self._live_player is not None:
            parent_proc = psutil.Process(self._live_player.pid)
            for child_proc in parent_proc.children(recursive=True):
                child_proc.kill()
            parent_proc.kill()
        if self.live_log is not None:
            self.live_log.close()
            self.live_log = None
        self.ws.close()

    def restart(self):
        print(">>>>>>>> AcWebsocket  RESTART <<<<<<<<<")
        self.close()
        self.run()

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

    def live_enter_room(self, uid: int, room_bans: [list, None] = None,
                        potplayer: [str, None] = None, quality: int = 1,
                        log_path: [str, os.PathLike, None] = None):
        if self._main_thread is None or self.is_close is True:
            self.run()
        if isinstance(potplayer, str) and os.path.isfile(potplayer):
            self.player_config = {"player_path": potplayer, "quality": quality}
        if log_path is not None:
            create_time = self.live_room.get('liveStartTime', 0) // 1000
            start_time = time.strftime('%Y%m%d', time.localtime(create_time))
            if os.path.isdir(log_path):
                live_log_path = os.path.join(log_path, f"AcLive({uid})_{start_time}.log")
                self.live_log = open(live_log_path, 'a')
            elif os.path.isfile(log_path) and log_path.endwith(".log"):
                self.live_log = open(log_path, 'a')
        self.live_room_msg_bans = [] if room_bans is None else room_bans
        self.live_obj = self.acer.AcLive().get(uid)
        cmd = self.protos.ZtLiveCsEnterRoom_Request(self.live_obj)
        return self.task(*cmd)

