"""单条收藏的编辑卡片：改评分 / 改状态 / 调进度。"""

_COLL_TYPE_LABEL = {1: "想看", 2: "看过", 3: "在看", 4: "搁置", 5: "抛弃"}
_COLL_TYPE_ORDER = [1, 3, 2, 4, 5]


def build_edit_collection_card(
    collection: dict,
    subject: dict,
    coll_type: str,
    page: int,
) -> dict:
    """collection: /users/-/collections/{sid} 返回；subject: 展开的 subject 字段或单独 subject 对象。"""
    subject_id = collection.get("subject_id") or subject.get("id")
    name = subject.get("name_cn") or subject.get("name") or "(无名)"
    eps = subject.get("eps") or subject.get("total_episodes") or 0
    ep_status = int(collection.get("ep_status") or 0)
    rate = int(collection.get("rate") or 0)
    cur_type = int(collection.get("type") or 0)

    rate_line = f"⭐ {rate}/10" if rate else "⭐ 未评分"
    progress_line = f"📖 {ep_status}/{eps or '?'}"
    status_line = f"🏷 {_COLL_TYPE_LABEL.get(cur_type, '—')}"

    header_md = (
        f"**[{name}](https://bgm.tv/subject/{subject_id})**\n"
        f"{status_line} · {progress_line} · {rate_line}"
    )

    def _btn(text: str, value: dict, disabled: bool = False, type_: str | None = None) -> dict:
        btn = {
            "tag": "button",
            "text": {"tag": "plain_text", "content": text},
            "value": value,
            "disabled": disabled,
        }
        if type_:
            btn["type"] = type_
        return btn

    # 评分 1-10，两行各 5 颗
    def _rate_row(start: int, end: int) -> dict:
        return {
            "tag": "action",
            "actions": [
                _btn(
                    f"{'⭐' if n == rate else ''}{n}",
                    {
                        "action": "rate",
                        "subject_id": subject_id,
                        "rate": n,
                        "type": coll_type,
                        "page": page,
                    },
                    type_="primary" if n == rate else None,
                )
                for n in range(start, end + 1)
            ],
        }

    # 收藏类型按顺序：想看 / 在看 / 看过 / 搁置 / 抛弃
    status_row = {
        "tag": "action",
        "actions": [
            _btn(
                _COLL_TYPE_LABEL[t],
                {
                    "action": "coll_type",
                    "subject_id": subject_id,
                    "coll_type": t,
                    "type": coll_type,
                    "page": page,
                },
                type_="primary" if t == cur_type else None,
            )
            for t in _COLL_TYPE_ORDER
        ],
    }

    progress_row = {
        "tag": "action",
        "actions": [
            _btn(
                "-1",
                {
                    "action": "ep_inc",
                    "subject_id": subject_id,
                    "ep_status": max(0, ep_status - 1),
                    "ep_from": ep_status,
                    "type": coll_type,
                    "page": page,
                    "view": "edit",
                },
                disabled=ep_status <= 0,
            ),
            _btn(
                f"第 {ep_status} 集",
                {"action": "noop"},
                disabled=True,
            ),
            _btn(
                "+1",
                {
                    "action": "ep_inc",
                    "subject_id": subject_id,
                    "ep_status": ep_status + 1,
                    "ep_from": ep_status,
                    "type": coll_type,
                    "page": page,
                    "view": "edit",
                },
                disabled=bool(eps) and ep_status >= int(eps),
                type_="primary",
            ),
        ],
    }

    back_row = {
        "tag": "action",
        "actions": [
            _btn(
                "返回",
                {
                    "action": "coll_detail",
                    "subject_id": subject_id,
                    "type": coll_type,
                    "page": page,
                },
            ),
            _btn(
                "返回列表",
                {"action": "page", "type": coll_type, "page": page},
            ),
        ],
    }

    return {
        "config": {"wide_screen_mode": True},
        "header": {
            "template": "blue",
            "title": {"tag": "plain_text", "content": f"✏️ 编辑收藏：{name}"},
        },
        "elements": [
            {"tag": "div", "text": {"tag": "lark_md", "content": header_md}},
            {"tag": "hr"},
            {"tag": "div", "text": {"tag": "lark_md", "content": "**状态**"}},
            status_row,
            {"tag": "div", "text": {"tag": "lark_md", "content": "**评分**"}},
            _rate_row(1, 5),
            _rate_row(6, 10),
            {"tag": "div", "text": {"tag": "lark_md", "content": "**进度**"}},
            progress_row,
            {"tag": "hr"},
            back_row,
        ],
    }
