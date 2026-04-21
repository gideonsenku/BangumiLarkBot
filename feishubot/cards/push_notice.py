"""订阅更新推送卡片。"""


def build_push_card(
    subject_id: int,
    title: str,
    volume: str = "",
    unsubscribed: bool = False,
) -> dict:
    """unsubscribed=True 用于取消订阅后的就地改写，隐藏按钮并换掉 header。"""
    if unsubscribed:
        header_title = "✅ 已取消订阅"
        header_template = "grey"
        body_md = f"**{title or f'subject {subject_id}'}**\n\n已取消该条目的更新推送。"
    else:
        header_title = "🌸 订阅更新"
        header_template = "green"
        tail = f"**{volume}** 已更新～" if volume else "有新内容～"
        name = title or f"subject {subject_id}"
        body_md = f"**[{name}](https://bgm.tv/subject/{subject_id})**\n\n{tail}"

    elements: list[dict] = [
        {"tag": "div", "text": {"tag": "lark_md", "content": body_md}}
    ]
    action_buttons: list[dict] = [
        {
            "tag": "button",
            "text": {"tag": "plain_text", "content": "查看详情"},
            "type": "primary",
            "url": f"https://bgm.tv/subject/{subject_id}",
        }
    ]
    if not unsubscribed:
        action_buttons.append(
            {
                "tag": "button",
                "text": {"tag": "plain_text", "content": "取消订阅"},
                "type": "default",
                "value": {
                    "action": "unsub",
                    "subject_id": subject_id,
                    "title": title,
                    "volume": volume,
                },
            }
        )
    elements.append({"tag": "action", "actions": action_buttons})

    return {
        "config": {"wide_screen_mode": True},
        "header": {
            "template": header_template,
            "title": {"tag": "plain_text", "content": header_title},
        },
        "elements": elements,
    }
