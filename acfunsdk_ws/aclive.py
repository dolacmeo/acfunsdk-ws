# coding=utf-8
import os
from .acws import AcWebSocket
from .reader import AcLiveReader

__author__ = 'dolacmeo'


class AcLiveRoom(AcWebSocket):
    live_obj = None

    def reader(self, seq_id: int, command, result):
        if command == 'Basic.ClientConfigGet':
            self._start_live()
        if command == 'LiveCmd.ZtLiveCsEnterRoomAck':
            self.task(*self.protos.ZtLiveCsHeartbeat_Request())
            self.task(*self.protos.ZtLiveInteractiveMessage_Request())
        elif command == "LiveCmd.ZtLiveCsHeartbeatAck" and seq_id % 5 == 0:
            self.task(*self.protos.ZtLiveInteractiveMessage_Request())
        self.output(seq_id, command, result)

    def output(self, seq_id: int, command, result):
        pass

    def _start_live(self):
        if self.live_obj is None:
            return False
        cmd = self.protos.ZtLiveCsEnterRoom_Request(self.live_obj.live)
        return self.task(*cmd)

    def enter_room(self, uid: int):
        self.live_obj = self.acer.acfun.AcLiveUp(uid)
        if self.live_obj.past_time < 0:
            return False
        if self._main_thread is None or self.is_close is True:
            self.run()
        return True


class AcLiveScreen(AcLiveRoom):
    live_reader = None

    def display(self, data: list):
        if self.live_reader is None:
            return None
        result = self.live_reader(data)
        for item in result:
            print(item)
        return True

    def output(self, seq_id: int, command, result):
        if command.startswith("LivePush.") and result:
            self.display(result)

    def enter_room(self, uid: int, msg_temp: [str, None] = None, filters: [dict, None] = None):
        self.live_obj = self.acer.acfun.AcLiveUp(uid)
        gifts = self.live_obj.gift_list()
        self.live_reader = AcLiveReader(gift=gifts, output_temp=msg_temp, filters=filters)
        if self.live_obj.past_time < 0:
            return False
        if self._main_thread is None or self.is_close is True:
            self.run()
        return True


class AcLiveDanmaku(AcLiveRoom):
    live_reader = None
    log_file_path = None

    def output(self, seq_id: int, command, result):
        if command.startswith("LivePush.") and result:
            if self.live_reader is None:
                return None
            data = self.live_reader(result)
            if len(data) == 0:
                return None
            with open(self.log_file_path, "a", encoding="utf8") as log:
                log.write("\n" + "\n".join(data))
            return True

    def enter_room(self, uid: int, log_path: [str, os.PathLike]):
        self.live_obj = self.acer.acfun.AcLiveUp(uid)
        if self.live_obj.past_time < 0:
            return False
        create_time = self.live_obj.raw_data.get("createTime", 0)
        self.log_file_path = os.path.join(log_path, f"{uid}_{create_time}.log")
        tmp = "{time}\t{user}\t{content}"
        filters = {"mtype": ["ZtLiveScActionSignal"], "signal": ["CommonActionSignalComment"]}
        self.live_reader = AcLiveReader(output_temp=tmp, filters=filters,
                                        time_tans=False, userid_only=True, type_name=False)
        if self._main_thread is None or self.is_close is True:
            self.run()
        return True
