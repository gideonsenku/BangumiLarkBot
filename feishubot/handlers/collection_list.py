import logging
import math

from utils import feishu_client
from utils.config_vars import bgm, sql
from utils.user_token import TokenExpired, get_valid_token

from ..cards.collection_list import build_collection_card
from ..cards.common import build_error_card, build_need_bind_card

logger = logging.getLogger(__name__)

PAGE_SIZE = 5


def handle_collection_list(open_id: str, coll_type: str, chat_id: str | None = None, page: int = 1) -> None:
    try:
        token_info = get_valid_token(open_id, sql, bgm)
    except TokenExpired:
        feishu_client.send_card(open_id, build_error_card("Bangumi 授权已失效，请发送 `/start` 重新绑定。"))
        return
    if not token_info:
        feishu_client.send_card(open_id, build_need_bind_card())
        return

    try:
        offset = (page - 1) * PAGE_SIZE
        data = bgm.list_collection(
            bgm_user_id=token_info["bgm_user_id"],
            coll_type=coll_type,
            limit=PAGE_SIZE,
            offset=offset,
            access_token=token_info["access_token"],
        )
    except Exception:
        logger.exception("list_collection failed")
        feishu_client.send_card(open_id, build_error_card("获取收藏失败，请稍后重试。"))
        return

    total = data.get("total", 0)
    total_pages = max(1, math.ceil(total / PAGE_SIZE))
    card = build_collection_card(
        items=data.get("data", []),
        page=page,
        total_pages=total_pages,
        coll_type=coll_type,
        total=total,
    )
    feishu_client.send_card(open_id, card)
