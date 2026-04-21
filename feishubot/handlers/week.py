import datetime
import logging

from utils import feishu_client
from utils.config_vars import bgm

from ..cards.common import build_error_card
from ..cards.week import build_week_card

logger = logging.getLogger(__name__)


def handle_week(open_id: str, weekday: int | None = None, chat_id: str | None = None) -> None:
    if weekday is None:
        # Python: Monday=0, Bangumi weekday.id: Monday=1
        weekday = datetime.datetime.now().weekday() + 1
    if weekday < 1 or weekday > 7:
        feishu_client.send_text(open_id, "用法：/week [1-7]，1=周一，7=周日")
        return
    try:
        calendar = bgm.calendar()
    except Exception as e:
        logger.exception("calendar failed")
        feishu_client.send_card(open_id, build_error_card(f"获取放送失败：`{e}`"))
        return
    feishu_client.send_card(open_id, build_week_card(calendar, weekday))
