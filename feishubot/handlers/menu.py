"""机器人自定义菜单点击分发。

菜单本身需在飞书开放平台 → 应用 → 机器人 → 自定义菜单里配置，代码侧仅处理点击事件。
用户点击时飞书推 application.bot.menu_v6，event.event_key 即菜单项的 key；
约定 key 前缀 `menu.`，下划线/点分段。菜单点击总发生在与机器人的 p2p 会话，所以
handler 默认用 open_id 作为投递目标（DM）。
"""

import logging

from utils import feishu_client

from ..cards.common import build_error_card
from .collection_list import handle_collection_list
from .help import handle_help
from .start import handle_start
from .unbind import handle_unbind
from .week import handle_week

logger = logging.getLogger(__name__)

_COLL_KEYS = {
    "menu.coll.anime": "anime",
    "menu.coll.book": "book",
    "menu.coll.real": "real",
    "menu.coll.game": "game",
    "menu.coll.music": "music",
}


def handle_menu_click(open_id: str, event_key: str) -> None:
    if not event_key:
        return
    if event_key in _COLL_KEYS:
        return handle_collection_list(open_id, _COLL_KEYS[event_key], open_id, page=1)
    if event_key == "menu.week":
        return handle_week(open_id, None, open_id)
    if event_key == "menu.start":
        return handle_start(open_id, open_id)
    if event_key == "menu.unbind":
        return handle_unbind(open_id, open_id)
    if event_key == "menu.help":
        return handle_help(open_id, open_id)
    logger.warning("unknown menu event_key: %s", event_key)
    feishu_client.send_card(open_id, build_error_card(f"未识别的菜单项：{event_key}"))
