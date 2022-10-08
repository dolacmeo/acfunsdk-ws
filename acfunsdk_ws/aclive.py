# coding=utf-8
import os
import json
import time
import psutil
import subprocess
from .acws import AcWebSocket
from .utils import ac_live_room_reader

__author__ = 'dolacmeo'


class AcLiveRoom(AcWebSocket):
    live_room = None
    player_config = None
    live_room_msg_bans = []
    live_room_gift = None
    live_obj = None
    live_log = None
    _live_player = None

    def reader(self, seq_id: int, command, result):
        if self.live_log is not None:
            self.live_log.write(json.dumps({
                "command": command,
                "message": result,
                "time": time.time(),
                "seqId": f"{seq_id}"
            }, separators=(',', ':')))
        if command == 'LiveCmd.ZtLiveCsEnterRoomAck':
            self.live_room = self.live_obj.live.raw_data
            self.live_room_gift = self.live_obj.gift_list()
            self.task(*self.protos.ZtLiveCsHeartbeat_Request())
            self.task(*self.protos.ZtLiveInteractiveMessage_Request())
            print(">>>>>>>> AcWebsocket EnterRoom <<<<<<<<")
            live_data = json.loads(self.live_room.get('videoPlayRes', "")).get('liveAdaptiveManifest', [])[0]
            live_adapt = live_data.get('adaptationSet', {}).get('representation', {})
            if self.player_config is None:
                print(f"未设置PotPlayer 请使用串流地址 请自行播放 \r\n {live_adapt[2]['url']}")
            else:
                create_time = self.live_room.get('liveStartTime', 0) // 1000
                start_time = time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(create_time))
                live_up_name = self.live_obj.username
                live_type = self.live_obj.raw.get("type", {})
                live_title = " ".join([
                    f"AcLive(#{self.live_obj.uid} @{live_up_name}| {live_type['categoryName']}>>{live_type['name']})",
                    self.live_room['caption'], f"🎬 {start_time}"
                ])
                potplayer = self.player_config['player_path']
                # print(f"[{potplayer}] 开始播放......\r\n {live_title}")
                live_obs_stream = live_adapt[self.player_config['quality']]['url']
                cmd_list = [potplayer, live_obs_stream, "/title", f'"{live_title}"']
                self._live_player = subprocess.Popen(cmd_list, creationflags=subprocess.CREATE_NO_WINDOW)
        if command.startswith("LivePush.") and result:
            msg = ac_live_room_reader(result, self.live_room_gift, self.live_room_msg_bans)
            for n in msg:
                print(n)

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
        default_bans = [
            # "ZtLiveScActionSignal",  # 互动消息
            "ZtLiveScStateSignal",  # 状态消息
            "ZtLiveScNotifySignal",  # 房管消息
        ]
        self.live_room_msg_bans = default_bans if room_bans is None else room_bans
        self.live_obj = self.acer.acfun.AcLiveUp(uid)
        cmd = self.protos.ZtLiveCsEnterRoom_Request(self.live_obj.live)
        return self.task(*cmd)
