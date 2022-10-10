# coding=utf-8
import time
import json
import base64

__author__ = 'dolacmeo'

message_types = {
    "ZtLiveScActionSignal":  "(粉丝互动)",
    "ZtLiveScStateSignal":   "(数据更新)",
    "ZtLiveScNotifySignal":  "(房管来啦)",
    "ZtLiveScStatusChanged": "(状态变更)",
    "ZtLiveScTicketInvalid": "(连接失效)[需要重连]",
}

signal_types = {
    "CommonActionSignalComment":                    "[送出弹幕]",
    "CommonActionSignalLike":                       "[爱心点赞]",
    "CommonActionSignalUserEnterRoom":              "[进入房间]",
    "CommonActionSignalUserFollowAuthor":           "[关注主播]",
    "AcfunActionSignalThrowBanana":                 "[投喂香蕉]",
    "CommonActionSignalGift":                       "[送出礼物]",
    "CommonActionSignalRichText":                   "[高级弹幕]",
    "AcfunActionSignalJoinClub":                    "[加守护团]",
    "AcfunStateSignalDisplayInfo":                  "[香蕉总数]",
    "CommonStateSignalDisplayInfo":                 "[在线人数][点赞数量]",
    "CommonStateSignalTopUsers":                    "[前三粉丝]",
    "CommonStateSignalRecentComment":               "[近期弹幕]",
    "CommonStateSignalChatCall":                    "[连麦被叫呼叫]",
    "CommonStateSignalChatAccept":                  "[连麦被叫接受]",
    "CommonStateSignalChatReady":                   "[连麦被叫等待]",
    "CommonStateSignalChatEnd":                     "[连麦被叫结束]",
    "CommonStateSignalCurrentRedpackList":          "[红包榜单]",
    "CommonStateSignalAuthorChatCall":              "[连麦主叫呼叫]",
    "CommonStateSignalAuthorChatAccept":            "[连麦主叫接受]",
    "CommonStateSignalAuthorChatReady":             "[连麦主叫等待]",
    "CommonStateSignalAuthorChatEnd":               "[连麦主叫结束]",
    "CommonStateSignalAuthorChatChangeSoundConfig": "[连麦主叫导播]",
    "CommonStateSignalPKAccept":                    "[连麦挑战接受]",
    "CommonStateSignalPKInvitation":                "[连麦挑战邀请]",
    "CommonStateSignalPKReady":                     "[连麦挑战等待]",
    "CommonStateSignalPKSoundConfigChanged":        "[连麦挑战导播]",
    "CommonStateSignalPkEnd":                       "[连麦挑战结束]",
    "CommonStateSignalPkStatistic":                 "[连麦挑战统计]",
    "CommonStateSignalWishSheetCurrentState":       "[愿望列表状态]",
    "CommonNotifySignalKickedOut":                  "[踢出房间]",
    "CommonNotifySignalViolationAlert":             "[违规警告]",
    "CommonNotifySignalLiveManagerState":           "[房管状态]",
}

signal_decodes = {
    "CommonActionSignalComment":            "💬{content}",
    "CommonStateSignalRecentComment":       "🗨️{content}",
    "CommonActionSignalLike":               "💕点赞了",
    "CommonActionSignalUserEnterRoom":      "🎟️进入直播间",
    "CommonActionSignalUserFollowAuthor":   "👀关注了主播",
    "AcfunActionSignalJoinClub":            "👥加入守护团",
    "AcfunActionSignalThrowBanana":         "🍌给主播投蕉",
    "CommonActionSignalGift":               "🎁送出{batchSize}个[{giftName}]"
}


def uint8_payload_to_base64(data: dict):
    """
    用于反解网页中等待encode的payload
    进入页面: https://message.acfun.cn/im
    调试js  : https://static.yximgs.com/udata/pkg/acfun-im/ImSdk.b0aeed.js
    进入页面: https://live.acfun.cn/live/
    设置断点: 9145  => e.payloadData
    调试js  : https://ali-imgs.acfun.cn/kos/nlav10360/static/js/3.867c7c46.js
    设置断点: 40910 => t
    return: base64encoded ==> https://protogen.marcgravell.com/decode
    """
    b_str = b''
    for x in range(len(data.keys())):
        b_str += bytes([data[str(x)]])
    return base64.standard_b64encode(b_str)


class AcLiveReader:
    temps = list()
    message_bans = list()
    gift_data = None
    filters = None
    config = dict()
    status = dict()
    notices = list()
    output_default = "{message}{signal}{time}{user}{content}"

    def __init__(self, /, **config):
        self.config = config
        self.filters = config.get("filters")
        self.gift_data = config.get("gift", {})

    def __call__(self, data: list):
        self.recv(data)
        return self.output()

    def recv(self, data: list):
        for item in data:
            # print(f"{item=}")
            signal_path = item['signal']
            if item['signal'].count(".") == 0:
                signal_path += "."
            msg_type, signal_name = signal_path.split(".")
            data_package = (msg_type, signal_name, item.get('payload'))
            if isinstance(self.filters, dict):
                if msg_type not in self.filters.get("mtype", []) or \
                        signal_name not in self.filters.get("signal", []):
                    # print(f"{msg_type=},{signal_name=}")
                    continue
            if signal_name in signal_decodes:
                self.decode(*data_package)
            elif "StateSignal" in signal_name:
                self._room_status(*data_package)
            elif "Notify" in signal_name:
                self._notify(*data_package)

    def output(self):
        # "message", "signal", "time", "user", "content"
        display = self.config.get("output_temp", self.output_default)
        if display is None:
            display = self.output_default
        result = list()
        for item in self.temps:
            result.append(display.format(**item))
        self.temps = list()
        return result

    @staticmethod
    def _user_info(data, id_only: bool = False):
        if data is None:
            return ""
        if id_only is True:
            return data['userId']
        base = f"<{data['userId']}@{data['nickname']}>"
        if 'badge' in data:
            badge = json.loads(data['badge']).get('medalInfo', {})
            base += f"『{badge['clubName']}|lv{badge['level']}』"
        return base

    @staticmethod
    def _unix2string(t: (int, float, str), f: str = "%H:%M:%S"):
        if len(str(t)) > 10:
            t = int(str(t)[:10])
        return time.strftime(f, time.localtime(t))

    def _room_status(self, mtype, signal, payload):
        if signal in ["AcfunStateSignalDisplayInfo", "CommonStateSignalDisplayInfo"]:
            keys = ["bananaCount", "watchingCount", "likeCount"]
            for x in keys:
                if x in payload:
                    self.status[x] = payload[x]
        elif signal in ["CommonStateSignalTopUsers"]:
            self.status["topUsers"] = payload['user']
        return True

    def _notify(self, mtype, signal, payload):
        keys = ["reason", "violationContent", "state"]
        for x in keys:
            if x in payload:
                self.notices.append(payload[x])
        return True

    def decode(self, mtype, signal, payload):
        if isinstance(payload, dict):
            if ["comment"] == list(payload.keys()):
                payload = payload.get("comment", [])
        for item in payload:
            mname, sname = mtype, signal
            if self.config.get("type_name", True) is True:
                mname = message_types.get(mtype)
                sname = signal_types.get(signal)
            stime = item.get("sendTimeMs")
            if self.config.get("time_tans", True) is True:
                stime = self._unix2string(stime)
            user = self._user_info(item.get("userInfo"), self.config.get("userid_only", False))
            content = signal_decodes.get(signal)
            if "content" in item:
                content = content.format(content=item.get("content"))
            elif signal == "CommonActionSignalGift":
                gift_name = f"{item.get('giftId')}"
                if isinstance(self.gift_data, dict):
                    gift_name = self.gift_data.get(gift_name, {}).get("giftName", "UNKNOWN")
                content = content.format(batchSize=item.get("batchSize"), giftName=gift_name)
                if item["comboCount"] > 1:
                    content += f" 连击{item['comboCount']}"
            elif signal == "CommonActionSignalRichText":
                print(item)
            self.temps.append(dict(zip(
                ["message", "signal", "time", "user", "content"],
                [mname, sname, stime, user, content]
            )))
