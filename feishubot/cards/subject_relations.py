"""条目关联卡片：分组列出，编号按钮下钻到子条目详情。"""

_TYPE_EMOJI = {1: "📚", 2: "🌸", 3: "🎵", 4: "🎮", 6: "📺"}

# 常见关联类别的展示顺序，对齐 TG 版
_RELATION_ORDER = {
    "原作": 1, "前作": 2, "前传": 3, "续作": 4, "续集": 5,
    "动画": 6, "游戏": 7, "番外篇": 8, "剧场版": 9, "总集篇": 10,
    "书籍": 11, "画集": 12, "衍生": 13, "原声集": 14, "角色歌": 15,
    "片头曲": 16, "片尾曲": 17, "插入歌": 18, "音乐": 19, "广播剧": 20,
    "其他": 100,
}

_MAX_RELATIONS = 18


def build_relations_card(
    parent_subject: dict,
    relations: list[dict],
    coll_type: str,
    page: int,
) -> dict:
    parent_name = parent_subject.get("name_cn") or parent_subject.get("name") or "(无名)"
    parent_id = parent_subject.get("id")

    if not relations:
        body_elements = [
            {
                "tag": "markdown",
                "content": f"_「{parent_name}」暂无关联条目。_",
            }
        ]
    else:
        sorted_rel = sorted(
            relations[:_MAX_RELATIONS],
            key=lambda r: _RELATION_ORDER.get(r.get("relation", "其他"), 99),
        )
        grouped: dict[str, list[dict]] = {}
        for r in sorted_rel:
            grouped.setdefault(r.get("relation") or "其他", []).append(r)

        lines: list[str] = []
        number_buttons: list[dict] = []
        idx = 1
        for relation_name, items in grouped.items():
            lines.append(f"**➤ {relation_name}**")
            for r in items:
                emoji = _TYPE_EMOJI.get(r.get("type"), "•")
                name = r.get("name_cn") or r.get("name") or "(无名)"
                rid = r.get("id")
                lines.append(
                    f"`{idx:02d}`. {emoji} [{name}](https://bgm.tv/subject/{rid})"
                )
                number_buttons.append(
                    {
                        "tag": "button",
                        "text": {"tag": "plain_text", "content": str(idx)},
                        "value": {
                            "action": "coll_detail",
                            "subject_id": rid,
                            "type": coll_type,
                            "page": page,
                            "back": "relations",
                            "parent_id": parent_id,
                        },
                    }
                )
                idx += 1
        body_elements = [
            {"tag": "div", "text": {"tag": "lark_md", "content": "\n".join(lines)}},
            {"tag": "action", "actions": number_buttons},
        ]

    body_elements.append(
        {
            "tag": "action",
            "actions": [
                {
                    "tag": "button",
                    "text": {"tag": "plain_text", "content": "返回"},
                    "value": {
                        "action": "coll_detail",
                        "subject_id": parent_id,
                        "type": coll_type,
                        "page": page,
                    },
                }
            ],
        }
    )

    return {
        "config": {"wide_screen_mode": True},
        "header": {
            "template": "blue",
            "title": {"tag": "plain_text", "content": f"🔗 {parent_name} · 关联条目"},
        },
        "elements": body_elements,
    }
