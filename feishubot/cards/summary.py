"""条目简介页：完整 summary + 返回按钮。"""

_TYPE_EMOJI = {1: "📚", 2: "🌸", 3: "🎵", 4: "🎮", 6: "📺"}

_SUMMARY_LIMIT = 1200


def build_summary_card(subject: dict, coll_type: str, page: int) -> dict:
    sid = subject.get("id")
    stype = subject.get("type")
    name_cn = subject.get("name_cn") or ""
    name = subject.get("name") or ""
    title = name_cn or name or "(无名)"
    subtitle = name if (name_cn and name and name_cn != name) else ""
    summary = (subject.get("summary") or "").strip() or "_暂无简介_"
    if len(summary) > _SUMMARY_LIMIT:
        summary = summary[:_SUMMARY_LIMIT] + "…"

    header_md = f"{_TYPE_EMOJI.get(stype, '•')} **{title}**"
    if subtitle:
        header_md += f"\n{subtitle}"

    body = (
        f"{header_md}\n\n"
        f"{summary}\n\n"
        f"📖 [详情](https://bgm.tv/subject/{sid}) · 💬 [吐槽箱](https://bgm.tv/subject/{sid}/comments)"
    )

    return {
        "config": {"wide_screen_mode": True},
        "header": {
            "template": "blue",
            "title": {"tag": "plain_text", "content": f"📝 {title} · 简介"},
        },
        "elements": [
            {"tag": "div", "text": {"tag": "lark_md", "content": body}},
            {
                "tag": "action",
                "actions": [
                    {
                        "tag": "button",
                        "text": {"tag": "plain_text", "content": "返回"},
                        "value": {
                            "action": "coll_detail",
                            "subject_id": sid,
                            "type": coll_type,
                            "page": page,
                        },
                    }
                ],
            },
        ],
    }
