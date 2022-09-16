# coding=utf-8
import time
import json
import base64

__author__ = 'dolacmeo'


# https://github.com/wpscott/AcFunDanmaku/blob/master/AcFunDanmu/README.md
# https://github.com/wpscott/AcFunDanmaku/blob/master/AcFunDanmu/data.md
# https://github.com/orzogc/acfundanmu/blob/master/proto.go
# https://developers.google.com/protocol-buffers/docs/pythontutorial
# https://websocket-client.readthedocs.io/en/latest/getting_started.html

# https://protogen.marcgravell.com/decode


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


def unix2string(t: (int, float, str), f: str = "%H:%M:%S"):
    if len(str(t)) > 10:
        t = int(str(t)[:10])
    return time.strftime(f, time.localtime(t))


message_types = {
    "ZtLiveScActionSignal": "(粉丝互动)",
    "ZtLiveScStateSignal": "(数据更新)",
    "ZtLiveScNotifySignal": "(房管来啦)",
    "ZtLiveScStatusChanged": "(状态变更)",
    "ZtLiveScTicketInvalid": "(连接失效)[需要重连]",
}

signal_types = {
    "CommonActionSignalComment": "[送出弹幕]",
    "CommonActionSignalLike": "[爱心点赞]",
    "CommonActionSignalUserEnterRoom": "[进入房间]",
    "CommonActionSignalUserFollowAuthor": "[关注主播]",
    "AcfunActionSignalThrowBanana": "[投喂香蕉]",
    "CommonActionSignalGift": "[送出礼物]",
    "CommonActionSignalRichText": "[高级弹幕]",
    "AcfunActionSignalJoinClub": "[加守护团]",
    "AcfunStateSignalDisplayInfo": "[香蕉总数]",
    "CommonStateSignalDisplayInfo": "[在线人数][点赞数量]",
    "CommonStateSignalTopUsers": "[前三粉丝]",
    "CommonStateSignalRecentComment": "[近期弹幕]",
    "CommonStateSignalChatCall": "[连麦被叫呼叫]",
    "CommonStateSignalChatAccept": "[连麦被叫接受]",
    "CommonStateSignalChatReady": "[连麦被叫等待]",
    "CommonStateSignalChatEnd": "[连麦被叫结束]",
    "CommonStateSignalCurrentRedpackList": "[红包榜单]",
    "CommonStateSignalAuthorChatCall": "[连麦主叫呼叫]",
    "CommonStateSignalAuthorChatAccept": "[连麦主叫接受]",
    "CommonStateSignalAuthorChatReady": "[连麦主叫等待]",
    "CommonStateSignalAuthorChatEnd": "[连麦主叫结束]",
    "CommonStateSignalAuthorChatChangeSoundConfig": "[连麦主叫导播]",
    "CommonStateSignalPKAccept": "[连麦挑战接受]",
    "CommonStateSignalPKInvitation": "[连麦挑战邀请]",
    "CommonStateSignalPKReady": "[连麦挑战等待]",
    "CommonStateSignalPKSoundConfigChanged": "[连麦挑战导播]",
    "CommonStateSignalPkEnd": "[连麦挑战结束]",
    "CommonStateSignalPkStatistic": "[连麦挑战统计]",
    "CommonStateSignalWishSheetCurrentState": "[愿望列表状态]",
    "CommonNotifySignalKickedOut": "[踢出房间]",
    "CommonNotifySignalViolationAlert": "[违规警告]",
    "CommonNotifySignalLiveManagerState": "[房管状态]",
}


def ac_live_room_reader(data: list, gift_data: [dict, None] = None, msg_bans: [list, None] = None):
    msg_bans = [] if msg_bans is None else msg_bans

    def user_info(payload_item):
        payload = payload_item['userInfo']
        base = f"<{payload['userId']}@{payload['nickname']}>"
        if 'badge' in payload:
            badge = json.loads(payload['badge']).get('medalInfo', {})
            base += f"『{badge['clubName']}|lv{badge['level']}』"
        return base

    messages = list()
    for item in data:
        signal_path = item['signal']
        if item['signal'].count(".") == 0:
            signal_path += "."
        msg_type, signal_name = signal_path.split(".")
        if msg_type in msg_bans:
            continue
        words = list()
        payload = item.get('payload')
        # 消息类型
        words.append(message_types.get(msg_type, "(????????)"))
        # 信号类型
        if signal_name:
            words.append(signal_types.get(signal_name, "[????????]"))
        # 内容信息
        if signal_name == "CommonActionSignalComment":
            words = list()
            for fans in payload:
                users = list()
                # 消息类型
                users.append(message_types.get(msg_type, "(????????)"))
                # 信号类型
                if signal_name:
                    users.append(signal_types.get(signal_name, "[????????]"))
                # 内容信息
                user = user_info(fans)
                content = fans['content']
                send_time = unix2string(fans['sendTimeMs'])
                users.append(f"{{{send_time}}} \r\n{user} 💬{content} \r\n")
                words.append("".join(users))
        elif signal_name == "CommonActionSignalLike":
            words = list()
            for fans in payload:
                users = list()
                # 消息类型
                users.append(message_types.get(msg_type, "(????????)"))
                # 信号类型
                if signal_name:
                    users.append(signal_types.get(signal_name, "[????????]"))
                # 内容信息
                user = user_info(fans)
                send_time = unix2string(fans['sendTimeMs'])
                users.append(f"{{{send_time}}} \r\n{user} 点赞了💖 \r\n")
                words.append("".join(users))
        elif signal_name == "CommonActionSignalUserEnterRoom":
            words = list()
            for newbee in payload:
                new_user = list()
                # 消息类型
                new_user.append(message_types.get(msg_type, "(????????)"))
                # 信号类型
                if signal_name:
                    new_user.append(signal_types.get(signal_name, "[????????]"))
                # 内容信息
                user = user_info(newbee)
                send_time = unix2string(int(newbee['sendTimeMs']))
                new_user.append(f"{{{send_time}}} \r\n{user} 进入直播间👤 \r\n")
                words.append("".join(new_user))
        elif signal_name == "CommonActionSignalUserFollowAuthor":
            words = list()
            for newbee in payload:
                new_user = list()
                # 消息类型
                new_user.append(message_types.get(msg_type, "(????????)"))
                # 信号类型
                if signal_name:
                    new_user.append(signal_types.get(signal_name, "[????????]"))
                # 内容信息
                user = user_info(newbee)
                send_time = unix2string(int(newbee['sendTimeMs']))
                words.append(f"{{{send_time}}} \r\n{user} 关注了主播👀 \r\n")
                words.append("".join(new_user))
        elif signal_name == "AcfunActionSignalThrowBanana":
            user = user_info(payload)
            send_time = unix2string(int(payload['sendTimeMs']))
            words.append(f"{{{send_time}}}{user}")
        elif signal_name == "CommonActionSignalGift":
            words = list()
            for fans in payload:
                users = list()
                # 消息类型
                users.append(message_types.get(msg_type, "(????????)"))
                # 信号类型
                if signal_name:
                    users.append(signal_types.get(signal_name, "[????????]"))
                # 内容信息
                user = user_info(fans)
                if gift_data is None:
                    gift = f"送出{fans['batchSize']}个🎁[{fans['giftId']}]"
                else:
                    gift = f"送出{fans['batchSize']}个🎁[{gift_data[str(fans['giftId'])]['giftName']}]"
                if fans['comboCount'] > 1:
                    gift += f" 连击{fans['comboCount']}"
                send_time = unix2string(fans['sendTimeMs'])
                words.append(f"{{{send_time}}} \r\n{user} {gift} \r\n")
                words.append("".join(users))
        elif signal_name == "CommonActionSignalRichText":
            # 高级弹幕
            # 包括发红包
            return data
        elif signal_name == "AcfunActionSignalJoinClub":
            words = list()
            for fans in payload:
                users = list()
                # 消息类型
                users.append(message_types.get(msg_type, "(????????)"))
                # 信号类型
                if signal_name:
                    users.append(signal_types.get(signal_name, "[????????]"))
                # 内容信息
                user = user_info(fans)
                send_time = unix2string(fans['sendTimeMs'])
                words.append(f"{{{send_time}}} \r\n{user} 加入守护团 \r\n")
                words.append("".join(users))
        elif signal_name == "AcfunStateSignalDisplayInfo":
            words.append(f"🍌x{payload['bananaCount']}")
        elif signal_name == "CommonStateSignalDisplayInfo":
            if 'watchingCount' in payload:
                words.append(f" 👤x{payload['watchingCount']}")
            if 'likeCount' in payload:
                words.append(f" ❤x{payload['likeCount']}")
        elif signal_name == "CommonStateSignalTopUsers":
            tops = [user_info(u) for u in payload['user']]
            words.append(f"\r\n🥇{tops[0]}")
            words.append(f"\r\n🥈{tops[1]}")
            words.append(f"\r\n🥉{tops[2]}")
        elif signal_name == "CommonStateSignalRecentComment":
            words = list()
            for comment in payload['comment']:
                his_words = list()
                # 消息类型
                his_words.append(message_types.get(msg_type, "(????????)"))
                # 信号类型
                if signal_name:
                    his_words.append(signal_types.get(signal_name, "[????????]"))
                # 内容信息
                user = user_info(comment)
                content = comment['content']
                send_time = unix2string(int(comment['sendTimeMs']))
                his_words.append(f"{{{send_time}}} \r\n{user} 💬{content}")
                full_comment = "".join(his_words) + "\r\n"
                words.append(full_comment)
        elif signal_name == "CommonNotifySignalKickedOut":
            words.append(f"{payload['reason']}")
        elif signal_name == "CommonNotifySignalViolationAlert":
            words.append(f"{payload['violationContent']}")
        elif signal_name == "CommonNotifySignalLiveManagerState":
            # MANAGER_STATE_UNKNOWN = 0
            # MANAGER_ADDED = 1
            # MANAGER_REMOVED = 2
            # IS_MANAGER = 3
            words.append(f"{payload['state']}")
        this_words = "".join(words)
        if this_words.endswith("\r\n"):
            this_words = this_words[:-2]
        messages.append(this_words)
    return messages
