import logging
import time

from .bgm_api import BgmApi

logger = logging.getLogger(__name__)

# token 剩余有效期少于此阈值（秒）即主动刷新
_REFRESH_THRESHOLD = 7 * 24 * 3600


class TokenExpired(Exception):
    """Token 刷新失败（区别于用户未绑定）。"""


def get_valid_token(open_id: str, sql, bgm: BgmApi) -> dict | None:
    """根据 open_id 返回 {access_token, bgm_user_id}，必要时自动刷新。

    - 未绑定：返回 None
    - 刷新失败：抛 TokenExpired（handler 应提示用户重新 /start）
    """
    user = sql.inquiry_user_data(open_id)
    if not user:
        return None

    if user["token_expires"] and user["token_expires"] - int(time.time()) < _REFRESH_THRESHOLD:
        try:
            new_token = bgm.oauth_refresh_token(user["refresh_token"])
            sql.update_user_token(
                open_id=open_id,
                access_token=new_token["access_token"],
                refresh_token=new_token["refresh_token"],
                token_expires=int(time.time()) + int(new_token.get("expires_in", 0)),
            )
            user["access_token"] = new_token["access_token"]
        except Exception as e:
            logger.warning("refresh token failed for %s: %s", open_id, e)
            raise TokenExpired(str(e)) from e

    return {
        "access_token": user["access_token"],
        "bgm_user_id": user["bgm_user_id"],
    }
