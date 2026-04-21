"""点格子卡片：以网格形式展示章节，带用户观看状态，支持点击切换。"""

import math

EPS_PAGE_SIZE = 12

_STATUS_EMOJI = {0: "⚪", 1: "👀", 2: "🔘", 3: "🗑️"}


def build_eps_grid_card(
    subject: dict,
    eps_data: list[dict],
    total: int,
    coll_type: str,
    page: int,
    ep_page: int,
    user_mode: bool,
) -> dict:
    """eps_data: 若 user_mode=True 为 list_user_episode_collections 返回的 {data:[{type, episode}]}。
    否则是 list_episodes 返回的 {data:[episode_dict]}。
    """
    name = subject.get("name_cn") or subject.get("name") or "(无名)"
    subject_id = subject.get("id")

    lines: list[str] = []
    number_buttons: list[dict] = []
    for item in eps_data:
        if user_mode:
            status = int(item.get("type") or 0)
            ep = item.get("episode") or {}
        else:
            status = 0
            ep = item
        sort_num = ep.get("sort") or ep.get("ep") or "?"
        ep_name = ep.get("name_cn") or ep.get("name") or "未公布"
        ep_id = ep.get("id")
        emoji = _STATUS_EMOJI.get(status, "⚪")
        lines.append(f"`{sort_num:>3}` {emoji} {ep_name}" if isinstance(sort_num, int) else f"`{sort_num}` {emoji} {ep_name}")
        if user_mode and ep_id:
            next_status = 0 if status == 2 else 2
            number_buttons.append(
                {
                    "tag": "button",
                    "text": {"tag": "plain_text", "content": f"{emoji}{sort_num}"},
                    "value": {
                        "action": "ep_toggle",
                        "subject_id": subject_id,
                        "ep_id": ep_id,
                        "status": next_status,
                        "type": coll_type,
                        "page": page,
                        "ep_page": ep_page,
                    },
                }
            )

    body_elements: list[dict] = []
    if lines:
        body_elements.append(
            {"tag": "div", "text": {"tag": "lark_md", "content": "\n".join(lines)}}
        )
    else:
        body_elements.append(
            {"tag": "div", "text": {"tag": "lark_md", "content": "_暂无章节_"}}
        )

    if number_buttons:
        body_elements.append({"tag": "action", "actions": number_buttons})

    total_pages = max(1, math.ceil(total / EPS_PAGE_SIZE))
    page_row = [
        {
            "tag": "button",
            "text": {"tag": "plain_text", "content": "⬅️ 上一页"},
            "value": {
                "action": "eps",
                "subject_id": subject_id,
                "type": coll_type,
                "page": page,
                "ep_page": max(1, ep_page - 1),
            },
            "disabled": ep_page <= 1,
        },
        {
            "tag": "button",
            "text": {"tag": "plain_text", "content": f"{ep_page} / {total_pages}"},
            "value": {"action": "noop"},
            "disabled": True,
        },
        {
            "tag": "button",
            "text": {"tag": "plain_text", "content": "下一页 ➡️"},
            "value": {
                "action": "eps",
                "subject_id": subject_id,
                "type": coll_type,
                "page": page,
                "ep_page": ep_page + 1,
            },
            "disabled": ep_page >= total_pages,
        },
    ]
    body_elements.append({"tag": "action", "actions": page_row})
    body_elements.append(
        {
            "tag": "action",
            "actions": [
                {
                    "tag": "button",
                    "text": {"tag": "plain_text", "content": "返回"},
                    "value": {
                        "action": "coll_detail",
                        "subject_id": subject_id,
                        "type": coll_type,
                        "page": page,
                    },
                }
            ],
        }
    )

    legend = "🔘 已看 · 👀 想看 · ⚪ 未看 · 🗑️ 抛弃" if user_mode else "_未绑定，仅浏览章节。_"
    body_elements.insert(
        0,
        {"tag": "div", "text": {"tag": "lark_md", "content": legend}},
    )

    return {
        "config": {"wide_screen_mode": True},
        "header": {
            "template": "blue",
            "title": {"tag": "plain_text", "content": f"🎞️ {name} · 点格子"},
        },
        "elements": body_elements,
    }
