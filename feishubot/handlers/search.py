import logging

from utils import feishu_client
from utils.config_vars import bgm

from ..cards.common import build_error_card
from ..cards.subject_info import build_search_result_card

logger = logging.getLogger(__name__)


def handle_search(
    open_id: str,
    keyword: str,
    chat_id: str | None = None,
    chat_type: str = "p2p",
) -> None:
    keyword = (keyword or "").strip()
    in_group = chat_type == "group" and chat_id
    if not keyword:
        if in_group:
            feishu_client.reply_text(chat_id, "用法：@机器人 <关键字> 或 /search <关键字>")
        else:
            feishu_client.send_text(open_id, "用法：/search <关键字>")
        return
    try:
        data = bgm.search(keyword, limit=10)
    except Exception as e:
        logger.exception("search failed")
        err = build_error_card(f"搜索失败：`{e}`")
        if in_group:
            feishu_client.reply_card(chat_id, err)
        else:
            feishu_client.send_card(open_id, err)
        return
    items = data.get("data") or data.get("list") or []
    card = build_search_result_card(keyword, items, in_group=bool(in_group))
    if in_group:
        feishu_client.reply_card(chat_id, card)
    else:
        feishu_client.send_card(open_id, card)
