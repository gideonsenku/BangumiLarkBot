from utils import feishu_client
from utils.config_vars import sql


def handle_unbind(open_id: str, chat_id: str | None = None) -> None:
    user = sql.inquiry_user_data(open_id)
    if not user:
        feishu_client.send_text(open_id, "你还没有绑定 Bangumi 账号。")
        return
    sql.delete_user_data(open_id)
    feishu_client.send_text(open_id, "已解除绑定。如需重新绑定请发送 /start。")
