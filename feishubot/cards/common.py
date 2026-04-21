"""通用卡片构造器：绑定、绑定成功、未绑定提示、错误。"""


def build_bind_card(auth_url: str) -> dict:
    return {
        "config": {"wide_screen_mode": True},
        "header": {
            "template": "blue",
            "title": {"tag": "plain_text", "content": "🔗 绑定 Bangumi 账号"},
        },
        "elements": [
            {
                "tag": "div",
                "text": {
                    "tag": "lark_md",
                    "content": "请点击下方按钮前往 Bangumi 完成授权。链接 10 分钟内有效。",
                },
            },
            {
                "tag": "action",
                "actions": [
                    {
                        "tag": "button",
                        "text": {"tag": "plain_text", "content": "前往授权"},
                        "type": "primary",
                        "url": auth_url,
                    }
                ],
            },
        ],
    }


def build_bind_success_card(bgm_user_id: int) -> dict:
    return {
        "config": {"wide_screen_mode": True},
        "header": {
            "template": "green",
            "title": {"tag": "plain_text", "content": "✅ 绑定成功"},
        },
        "elements": [
            {
                "tag": "div",
                "text": {
                    "tag": "lark_md",
                    "content": (
                        f"已绑定 Bangumi 用户 **{bgm_user_id}**。\n"
                        "可用指令：/anime /book /game /music /real /search /week /help"
                    ),
                },
            }
        ],
    }


def build_need_bind_card() -> dict:
    return {
        "config": {"wide_screen_mode": True},
        "header": {
            "template": "orange",
            "title": {"tag": "plain_text", "content": "⚠️ 尚未绑定"},
        },
        "elements": [
            {
                "tag": "div",
                "text": {"tag": "lark_md", "content": "请先发送 `/start` 绑定 Bangumi 账号。"},
            }
        ],
    }


def build_error_card(message: str) -> dict:
    return {
        "config": {"wide_screen_mode": True},
        "header": {
            "template": "red",
            "title": {"tag": "plain_text", "content": "❌ 出错了"},
        },
        "elements": [
            {"tag": "div", "text": {"tag": "lark_md", "content": message}}
        ],
    }


def build_help_card() -> dict:
    commands = [
        ("/start", "绑定 Bangumi 账号"),
        ("/unbind", "解除绑定"),
        ("/anime", "在看动画"),
        ("/book", "在读书籍"),
        ("/game", "在玩游戏"),
        ("/music", "在听音乐"),
        ("/real", "在看剧集"),
        ("/search <关键字>", "搜索条目"),
        ("/week [1-7]", "每日放送（空=今日）"),
        ("/help", "显示此帮助"),
    ]
    lines = "\n".join(f"• `{cmd}` — {desc}" for cmd, desc in commands)
    return {
        "config": {"wide_screen_mode": True},
        "header": {
            "template": "blue",
            "title": {"tag": "plain_text", "content": "📖 Bangumi Feishu Bot"},
        },
        "elements": [
            {"tag": "div", "text": {"tag": "lark_md", "content": lines}}
        ],
    }
