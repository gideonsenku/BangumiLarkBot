"""收藏列表翻页卡片：仅编号 + 翻页，点编号后由 detail 卡片接管。"""

_TYPE_LABEL = {
    "anime": "🎬 在看动画",
    "book": "📚 在读书籍",
    "game": "🎮 在玩游戏",
    "music": "🎵 在听音乐",
    "real": "📺 在看剧集",
}

_NUM_CIRCLED = ["①", "②", "③", "④", "⑤", "⑥", "⑦", "⑧", "⑨", "⑩"]


def build_collection_card(
    items: list[dict],
    page: int,
    total_pages: int,
    coll_type: str,
    total: int | None = None,
) -> dict:
    elements: list[dict] = []
    if not items:
        elements.append(
            {"tag": "div", "text": {"tag": "lark_md", "content": "_暂无收藏_"}}
        )

    lines: list[str] = []
    number_buttons: list[dict] = []
    for idx, it in enumerate(items[:10], start=1):
        subject = it.get("subject", {}) or {}
        name = subject.get("name_cn") or subject.get("name") or "(无名)"
        eps = subject.get("eps") or subject.get("total_episodes") or "?"
        ep_status = it.get("ep_status", 0)
        subject_id = it.get("subject_id") or subject.get("id")
        rate = it.get("rate") or 0
        score = f" ⭐{rate}" if rate else ""
        circled = _NUM_CIRCLED[idx - 1]
        lines.append(
            f"**{circled}** [{name}](https://bgm.tv/subject/{subject_id}) "
            f"`[{ep_status}/{eps}]`{score}"
        )
        number_buttons.append(
            {
                "tag": "button",
                "text": {"tag": "plain_text", "content": str(idx)},
                "value": {
                    "action": "coll_detail",
                    "subject_id": subject_id,
                    "type": coll_type,
                    "page": page,
                },
            }
        )

    if lines:
        elements.append(
            {"tag": "div", "text": {"tag": "lark_md", "content": "\n\n".join(lines)}}
        )
        # 编号按钮一行，飞书 action 容器会自动换行
        elements.append({"tag": "action", "actions": number_buttons})

    # 翻页
    total_pages = max(1, total_pages)
    page_buttons: list[dict] = [
        {
            "tag": "button",
            "text": {"tag": "plain_text", "content": "⬅️ 上一页"},
            "value": {"action": "page", "type": coll_type, "page": max(1, page - 1)},
            "disabled": page <= 1,
        },
        {
            "tag": "button",
            "text": {"tag": "plain_text", "content": f"{page} / {total_pages}"},
            "value": {"action": "noop"},
            "disabled": True,
        },
        {
            "tag": "button",
            "text": {"tag": "plain_text", "content": "下一页 ➡️"},
            "value": {"action": "page", "type": coll_type, "page": page + 1},
            "disabled": page >= total_pages,
        },
    ]
    elements.append({"tag": "action", "actions": page_buttons})

    header_title = _TYPE_LABEL.get(coll_type, coll_type)
    if total is not None:
        header_title = f"{header_title} · 共 {total} 部"

    return {
        "config": {"wide_screen_mode": True},
        "header": {
            "template": "blue",
            "title": {"tag": "plain_text", "content": header_title},
        },
        "elements": elements,
    }
