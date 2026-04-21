import logging
import re

from utils import feishu_client
from utils.config_vars import bgm

from ..cards.common import build_error_card
from ..cards.subject_info import build_subject_detail_card

logger = logging.getLogger(__name__)

_LINK_RE = re.compile(r"(?:bgm\.tv|bangumi\.tv|chii\.in)/subject/(\d+)", re.IGNORECASE)


def extract_subject_ids(text: str) -> list[int]:
    return [int(m) for m in _LINK_RE.findall(text or "")]


def handle_info(open_id: str, subject_id: int, chat_id: str | None = None) -> None:
    try:
        subject = bgm.get_subject(subject_id)
    except Exception as e:
        logger.exception("get_subject failed")
        feishu_client.send_card(open_id, build_error_card(f"获取条目失败：`{e}`"))
        return
    feishu_client.send_card(open_id, build_subject_detail_card(subject))
