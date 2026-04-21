"""消息 / 卡片动作路由。

飞书事件 payload 的字段可能随 SDK 版本微变；以下实现围绕事件 event body 的 JSON
提取关键字段，尽量不依赖 SDK 模型层的强类型结构，以降低版本耦合。
"""

import json
import logging
import re
import threading

from utils import feishu_client
from utils.config_vars import BOT_OPEN_ID, redis

from .handlers import (
    handle_card_action,
    handle_collection_list,
    handle_help,
    handle_info,
    handle_menu_click,
    handle_search,
    handle_start,
    handle_unbind,
    handle_url_preview,
    handle_week,
)
from .handlers.info import extract_subject_ids

logger = logging.getLogger(__name__)

_COLLECTION_TYPES = {"anime", "book", "game", "music", "real"}
_CMD_RE = re.compile(r"^/(\w+)(?:\s+(.*))?$", re.DOTALL)


def _dedupe(event_id: str) -> bool:
    """基于 event_id 做 10 分钟幂等去重。返回 True 表示首次到达。"""
    if not event_id:
        return True
    key = f"event:{event_id}"
    return redis.set(key, "1", nx=True, ex=600) is True


def _extract_text(message: dict) -> tuple[str, bool]:
    """从 message payload 提取 (纯文本, 机器人是否被 @)。

    飞书群消息默认仅在 @机器人 时投递，但若应用开启「接收全部群消息」权限则所有文本
    都会进来；因此需要额外区分是否真的 @ 到了机器人。
    优先以 message.mentions[i].id.open_id 对比 BOT_OPEN_ID（需在 .env 配置 FEISHU_BOT_OPEN_ID）；
    未配置时退化为「文本包含 @_user_ 占位符」的弱判断，可能误触发。
    """
    msg_type = message.get("message_type") or message.get("msg_type")
    content_raw = message.get("content") or "{}"
    try:
        content = json.loads(content_raw) if isinstance(content_raw, str) else content_raw
    except json.JSONDecodeError:
        return "", False
    if msg_type != "text":
        return "", False
    raw = content.get("text", "")
    text = re.sub(r"@_user_\d+\s*", "", raw).strip()
    mentions = message.get("mentions") or []
    bot_id = BOT_OPEN_ID or feishu_client.get_bot_open_id()
    if bot_id:
        bot_mentioned = any(
            ((m.get("id") or {}).get("open_id") == bot_id) for m in mentions
        )
    else:
        bot_mentioned = "@_user_" in raw
    return text, bot_mentioned


def _dispatch_text(
    open_id: str,
    chat_id: str,
    text: str,
    chat_type: str = "p2p",
    bot_mentioned: bool = False,
) -> None:
    text = text.strip()
    m = _CMD_RE.match(text)
    if m:
        cmd = m.group(1).lower()
        arg = (m.group(2) or "").strip()
        if cmd == "start":
            return handle_start(open_id, chat_id)
        if cmd == "help":
            return handle_help(open_id, chat_id)
        if cmd == "unbind":
            return handle_unbind(open_id, chat_id)
        if cmd in _COLLECTION_TYPES:
            return handle_collection_list(open_id, cmd, chat_id, page=1)
        if cmd == "search":
            return handle_search(open_id, arg, chat_id, chat_type)
        if cmd == "week":
            try:
                weekday = int(arg) if arg else None
            except ValueError:
                weekday = None
            return handle_week(open_id, weekday, chat_id)
        if cmd == "info":
            try:
                sid = int(arg)
            except ValueError:
                return handle_help(open_id, chat_id)
            return handle_info(open_id, sid, chat_id)
        return handle_help(open_id, chat_id)

    # 未命中指令：若文本包含 bgm 链接则展开
    sids = extract_subject_ids(text)
    if sids:
        return handle_info(open_id, sids[0], chat_id)

    # 群聊中 @机器人 + 纯文本：当作搜索关键字；未 @ 到机器人则忽略
    if chat_type == "group" and text and bot_mentioned:
        return handle_search(open_id, text, chat_id, chat_type)


def on_message_event(data: dict) -> None:
    """处理 im.message.receive_v1。data 为 event 整体字典。"""
    try:
        header = data.get("header") or {}
        event_id = header.get("event_id") or ""
        if not _dedupe(event_id):
            logger.debug("duplicate event %s, skip", event_id)
            return

        event = data.get("event") or {}
        sender = event.get("sender") or {}
        sender_id = sender.get("sender_id") or {}
        open_id = sender_id.get("open_id") or ""
        if not open_id:
            return
        message = event.get("message") or {}
        chat_id = message.get("chat_id") or ""
        chat_type = message.get("chat_type") or "p2p"
        text, bot_mentioned = _extract_text(message)
        if not text:
            return
        _dispatch_text(open_id, chat_id, text, chat_type, bot_mentioned)
    except Exception:
        logger.exception("on_message_event failed")


def on_url_preview_event(data: dict) -> dict:
    """处理 url.preview.get_v1。必须同步返回 {inline, card} dict（≤3s）。

    与 message/card 事件不同：这里不做 event_id 幂等 —— 飞书可能对同一条消息
    多次请求预览（刷新、缓存失效），每次都要返回新鲜数据。
    """
    try:
        event = data.get("event") or {}
        ctx = event.get("context") or {}
        url = ctx.get("url") or ""
        return handle_url_preview(url)
    except Exception:
        logger.exception("on_url_preview_event failed")
        from .cards.url_preview import build_preview_error
        return build_preview_error()


def on_menu_event(data: dict) -> None:
    """处理 application.bot.menu_v6。菜单点击总在与机器人的 p2p 会话里发生。"""
    try:
        header = data.get("header") or {}
        event_id = header.get("event_id") or ""
        if event_id and not _dedupe(event_id):
            return
        event = data.get("event") or {}
        operator = event.get("operator") or {}
        # 菜单事件里 operator 结构为 {operator_id: {open_id, ...}}，和其他事件不一致
        op_id = operator.get("operator_id") or {}
        open_id = op_id.get("open_id") or operator.get("open_id") or ""
        event_key = event.get("event_key") or ""
        if not open_id or not event_key:
            return
        threading.Thread(
            target=handle_menu_click,
            args=(open_id, event_key),
            daemon=True,
        ).start()
    except Exception:
        logger.exception("on_menu_event failed")


def on_card_event(data: dict) -> dict | None:
    """处理 card.action.trigger。返回 dict 会被 SDK 作为回调响应发送。"""
    try:
        header = data.get("header") or {}
        event_id = header.get("event_id") or ""
        if event_id and not _dedupe(event_id):
            return None

        event = data.get("event") or {}
        operator = event.get("operator") or {}
        open_id = operator.get("open_id") or ""
        action = event.get("action") or {}
        value = action.get("value") or {}
        # 飞书新版卡片回调结构：event.context.open_message_id / open_chat_id
        ctx = event.get("context") or {}
        message_id = ctx.get("open_message_id") or event.get("open_message_id") or ""
        if not open_id or not value:
            return None
        # 异步化：业务在后台线程执行，立即回 ACK 避免 3s 超时
        threading.Thread(
            target=handle_card_action,
            args=(open_id, value, message_id),
            daemon=True,
        ).start()
        return {"toast": {"type": "info", "content": "处理中…"}}
    except Exception:
        logger.exception("on_card_event failed")
        return None
