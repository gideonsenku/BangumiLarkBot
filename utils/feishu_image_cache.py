"""BGM 封面 → 飞书 image_key 的缓存层。

飞书卡片不渲染外链图片，必须先上传拿 img_key。同一张 BGM 封面可能被多用户/多次
展示，缓存到 Redis 避免重复上传。默认缓存 30 天（image_key 本身长期有效）。
"""

import logging

import requests

from . import feishu_client
from .config_vars import redis

logger = logging.getLogger(__name__)

_CACHE_PREFIX = "feishu:imgkey:"
_CACHE_TTL = 30 * 24 * 3600
_UA = "BangumiFeishuBot/0.1"


def get_img_key(image_url: str) -> str | None:
    """拉取 URL → 上传飞书 → 返回 image_key；任意失败返回 None（调用方回退为链接）。"""
    if not image_url:
        return None
    cached = redis.get(_CACHE_PREFIX + image_url)
    if cached:
        return cached.decode() if isinstance(cached, bytes) else cached
    try:
        resp = requests.get(image_url, headers={"User-Agent": _UA}, timeout=8)
        resp.raise_for_status()
        key = feishu_client.upload_image(resp.content)
    except Exception:
        logger.exception("fetch/upload image failed: %s", image_url)
        return None
    try:
        redis.set(_CACHE_PREFIX + image_url, key, ex=_CACHE_TTL)
    except Exception:
        logger.warning("cache img_key failed", exc_info=True)
    return key
