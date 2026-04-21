"""飞书 bot 启动与关闭。使用 lark.ws.Client 长连接接收事件。"""

import asyncio
import json
import logging
import threading

import lark_oapi as lark

from utils import feishu_client
from utils.config_vars import FEISHU_APP_ID, FEISHU_APP_SECRET, FEISHU_TRANSPORT

from .dispatcher import on_card_event, on_menu_event, on_message_event, on_url_preview_event

logger = logging.getLogger(__name__)

_ws_client: lark.ws.Client | None = None
_ws_thread: threading.Thread | None = None


def _build_event_handler() -> lark.EventDispatcherHandler:
    def _msg_adapter(req):
        logger.info("== message event received ==")
        try:
            raw = lark.JSON.marshal(req)
            logger.info("message payload: %s", raw)
            data = json.loads(raw)
        except Exception as e:
            logger.warning("marshal failed: %s; fallback to __dict__", e)
            data = getattr(req, "__dict__", {}) or {}
        on_message_event(data)

    def _card_adapter(req):
        logger.info("== card action received ==")
        try:
            raw = lark.JSON.marshal(req)
            logger.info("card payload: %s", raw)
            data = json.loads(raw)
        except Exception as e:
            logger.warning("marshal failed: %s; fallback to __dict__", e)
            data = getattr(req, "__dict__", {}) or {}
        return on_card_event(data)

    def _preview_adapter(req):
        logger.info("== url preview received ==")
        try:
            raw = lark.JSON.marshal(req)
            logger.info("preview payload: %s", raw)
            data = json.loads(raw)
        except Exception as e:
            logger.warning("marshal failed: %s; fallback to __dict__", e)
            data = getattr(req, "__dict__", {}) or {}
        return on_url_preview_event(data)

    def _menu_adapter(req):
        logger.info("== bot menu clicked ==")
        try:
            raw = lark.JSON.marshal(req)
            logger.info("menu payload: %s", raw)
            data = json.loads(raw)
        except Exception as e:
            logger.warning("marshal failed: %s; fallback to __dict__", e)
            data = getattr(req, "__dict__", {}) or {}
        on_menu_event(data)

    return (
        lark.EventDispatcherHandler.builder("", "")
        .register_p2_im_message_receive_v1(_msg_adapter)
        .register_p2_card_action_trigger(_card_adapter)
        .register_p2_url_preview_get(_preview_adapter)
        .register_p2_application_bot_menu_v6(_menu_adapter)
        .build()
    )


async def start_bot() -> None:
    """启动 ws 长连。lark.ws.Client.start() 是同步且自带 event loop，放独立线程跑。"""
    global _ws_client, _ws_thread
    if FEISHU_TRANSPORT != "websocket":
        logger.warning("当前 TRANSPORT=%s；MVP 仅实现 websocket 长连，退出 bot 循环", FEISHU_TRANSPORT)
        return

    handler = _build_event_handler()
    _ws_client = lark.ws.Client(
        FEISHU_APP_ID,
        FEISHU_APP_SECRET,
        event_handler=handler,
        log_level=lark.LogLevel.DEBUG,
    )

    bot_id = feishu_client.get_bot_open_id()
    if bot_id:
        logger.info("bot open_id = %s（可填入 .env 的 FEISHU_BOT_OPEN_ID 跳过每次自动拉取）", bot_id)
    else:
        logger.warning("无法获取 bot open_id；群 @ 检测将降级为弱匹配")

    logger.info("feishu bot starting (ws long-connection)…")
    _ws_thread = threading.Thread(target=_ws_client.start, name="lark-ws", daemon=True)
    _ws_thread.start()

    # 主协程保持存活，交由外层 stop_event 控制退出
    stop_forever = asyncio.Event()
    try:
        await stop_forever.wait()
    except asyncio.CancelledError:
        pass


async def stop_bot() -> None:
    global _ws_client, _ws_thread
    if _ws_client is not None:
        try:
            # lark 的 _disconnect 是协程；由于它在独立线程里管理自己的 loop，
            # 这里直接置 None 即可（daemon 线程随进程退出）。
            pass
        except Exception:
            pass
    _ws_client = None
    _ws_thread = None
