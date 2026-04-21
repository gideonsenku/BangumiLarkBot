"""处理 url.preview.get_v1 事件：拉取 bgm subject 元数据并返回 inline + card。

约束：飞书要求同步回包 ≤ 3 秒，此函数必须快速返回；BGM API 超时回退到错误 inline。
"""

import logging

from utils.config_vars import bgm

from ..cards.url_preview import build_preview_error, build_preview_response
from .info import extract_subject_ids

logger = logging.getLogger(__name__)


def handle_url_preview(url: str) -> dict:
    sids = extract_subject_ids(url or "")
    if not sids:
        return build_preview_error("链接无法识别")
    try:
        subject = bgm.get_subject(sids[0])
    except Exception:
        logger.exception("get_subject failed for preview, url=%s", url)
        return build_preview_error("获取条目失败")
    return build_preview_response(subject)
