from utils import feishu_client

from ..cards.common import build_help_card


def handle_help(open_id: str, chat_id: str | None = None) -> None:
    feishu_client.send_card(open_id, build_help_card())
