import json
import logging
import time
import uuid

from utils import feishu_client
from utils.config_vars import API_WEBSITE_BASE, CALLBACK_URL, bgm, redis, sql
from utils.user_token import TokenExpired, get_valid_token

from ..cards.common import build_bind_card, build_bind_success_card

logger = logging.getLogger(__name__)


def handle_start(open_id: str, chat_id: str | None = None) -> None:
    existing = sql.inquiry_user_data(open_id)
    if existing:
        # 检查 token 仍然有效；失效则落到新 OAuth 让用户重绑（回调会 upsert 覆写）。
        try:
            get_valid_token(open_id, sql, bgm)
            feishu_client.send_card(open_id, build_bind_success_card(existing["bgm_user_id"]))
            return
        except TokenExpired:
            logger.info("start: token expired for %s, re-binding", open_id)

    state = uuid.uuid4().hex
    payload = {"open_id": open_id, "ts": int(time.time())}
    redis.setex(f"oauth:{state}", 600, json.dumps(payload))

    auth_url = f"{API_WEBSITE_BASE.rstrip('/')}/oauth_index?state={state}"
    feishu_client.send_card(open_id, build_bind_card(auth_url))
    logger.info("start: open_id=%s state=%s", open_id, state)
