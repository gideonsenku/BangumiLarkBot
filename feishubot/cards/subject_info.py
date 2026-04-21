"""条目详情 / 搜索结果卡片。"""

import html

from utils.feishu_image_cache import get_img_key

_TYPE_EMOJI = {1: "📚", 2: "🌸", 3: "🎵", 4: "🎮", 6: "📺"}
_TYPE_NAME = {1: "书籍", 2: "动画", 3: "音乐", 4: "游戏", 6: "剧集"}


def _infobox_get(infobox: list, key: str) -> str | None:
    for box in infobox or []:
        if box.get("key") == key:
            v = box.get("value")
            if isinstance(v, list):
                return " / ".join(item.get("v", "") for item in v if isinstance(item, dict))
            return str(v) if v is not None else None
    return None


def build_subject_card(subject: dict) -> dict:
    name = subject.get("name_cn") or subject.get("name") or "(无名)"
    subject_id = subject.get("id")
    summary = subject.get("summary") or ""
    if len(summary) > 200:
        summary = summary[:200] + "…"
    rating = (subject.get("rating") or {}).get("score") or "-"
    total = (subject.get("rating") or {}).get("total") or 0
    eps = subject.get("eps") or subject.get("total_episodes") or "-"
    images = subject.get("images") or {}
    image_url = images.get("large") or images.get("common") or ""

    img_key = get_img_key(image_url) if image_url else None
    cover_line = "" if img_key else (f"\n[🖼 封面]({image_url})" if image_url else "")
    elements: list[dict] = []
    if img_key:
        elements.append(
            {
                "tag": "img",
                "img_key": img_key,
                "alt": {"tag": "plain_text", "content": name},
                "mode": "fit_horizontal",
            }
        )
    elements.append(
        {
            "tag": "div",
            "text": {
                "tag": "lark_md",
                "content": (
                    f"**[{name}](https://bgm.tv/subject/{subject_id})**\n"
                    f"⭐ {rating} ({total} 人评分) · 共 {eps} 话{cover_line}\n\n"
                    f"{summary}"
                ),
            },
        }
    )
    elements.append(
        {
            "tag": "action",
            "actions": [
                {
                    "tag": "button",
                    "text": {"tag": "plain_text", "content": "查看详情"},
                    "url": f"https://bgm.tv/subject/{subject_id}",
                    "type": "primary",
                },
                {
                    "tag": "button",
                    "text": {"tag": "plain_text", "content": "订阅更新"},
                    "value": {"action": "sub", "subject_id": subject_id},
                },
            ],
        }
    )
    return {
        "config": {"wide_screen_mode": True},
        "header": {
            "template": "turquoise",
            "title": {"tag": "plain_text", "content": f"🔎 {name}"},
        },
        "elements": elements,
    }


def build_search_result_card(keyword: str, items: list[dict], in_group: bool = False) -> dict:
    if not items:
        return {
            "config": {"wide_screen_mode": True},
            "header": {
                "template": "grey",
                "title": {"tag": "plain_text", "content": f"🔎 未找到与「{keyword}」相关的条目"},
            },
            "elements": [
                {"tag": "div", "text": {"tag": "lark_md", "content": "请尝试更换关键字。"}}
            ],
        }

    elements: list[dict] = []
    for it in items[:10]:
        name = it.get("name_cn") or it.get("name") or "(无名)"
        sid = it.get("id")
        rating = (it.get("rating") or {}).get("score") or "-"
        stype = it.get("type")
        emoji = _TYPE_EMOJI.get(stype, "")
        elements.append(
            {
                "tag": "div",
                "text": {
                    "tag": "lark_md",
                    "content": f"{emoji} **[{name}](https://bgm.tv/subject/{sid})** ⭐ {rating}",
                },
                "extra": {
                    "tag": "button",
                    "text": {"tag": "plain_text", "content": "详情"},
                    "type": "primary",
                    "value": {"action": "detail", "subject_id": sid, "g": 1 if in_group else 0},
                },
            }
        )
    return {
        "config": {"wide_screen_mode": True},
        "header": {
            "template": "turquoise",
            "title": {"tag": "plain_text", "content": f"🔎 搜索结果：{keyword}"},
        },
        "elements": elements,
    }


_TAG_COLORS = ["blue", "violet", "purple"]


def _build_meta_lines(stype: int, sid, type_name: str, platform: str, date: str, eps, infobox: list) -> list[str]:
    lines = [f"**BGM ID** ：`{sid}` · **类型** ：{type_name}"]
    if stype in (2, 6):
        label = "剧集类型" if stype == 6 else "放送类型"
        if platform:
            lines.append(f"**{label}** ：`{platform}`")
        lines.append(f"**放送开始** ：`{date}` · **集数** ：`{eps}`")
    elif stype == 1:
        lines.append(f"**书籍类型** ：`{platform}` · **发售** ：`{date}`")
        for key in ("作者", "出版社", "页数"):
            v = _infobox_get(infobox, key)
            if v:
                lines.append(f"**{key}** ：`{v}`")
    elif stype == 3:
        lines.append(f"**发售日期** ：`{date}`")
        for key in ("艺术家", "作曲", "作词", "厂牌", "碟片数量", "播放时长"):
            v = _infobox_get(infobox, key)
            if v:
                lines.append(f"**{key}** ：`{html.unescape(v)}`")
    elif stype == 4:
        lines.append(f"**发行日期** ：`{date}`")
        for key in ("游戏类型", "平台", "发行", "游玩人数"):
            v = _infobox_get(infobox, key)
            if v:
                lines.append(f"**{key}** ：`{v}`")
    return lines


def build_subject_body_elements(subject: dict, summary_limit: int = 400) -> list[dict]:
    """左右双栏 meta/评分 + 简介 + 半幅海报。供条目详情类卡片复用。"""
    sid = subject.get("id")
    stype = subject.get("type")
    type_name = _TYPE_NAME.get(stype, "")
    rating_obj = subject.get("rating") or {}
    score = rating_obj.get("score") or 0
    total = rating_obj.get("total") or 0
    rank = rating_obj.get("rank") or 0
    date = subject.get("date") or "未知"
    eps = subject.get("eps") or subject.get("total_episodes") or 0
    platform = subject.get("platform") or ""
    nsfw = subject.get("nsfw")
    infobox = subject.get("infobox") or []
    summary = (subject.get("summary") or "").strip()
    images = subject.get("images") or {}
    image_url = images.get("large") or images.get("common") or ""
    img_key = get_img_key(image_url) if image_url else None

    meta_lines = _build_meta_lines(stype, sid, type_name, platform, date, eps, infobox)
    if nsfw:
        meta_lines.append("🔞 **NSFW**")

    tags = subject.get("tags") or []
    tag_parts = [
        f"<font color='{_TAG_COLORS[i % len(_TAG_COLORS)]}'>{t['name']}</font>"
        for i, t in enumerate(tags[:10])
        if t.get("name")
    ]
    tags_md = f"**标签** ：{' '.join(tag_parts)}" if tag_parts else ""

    left_elements = [{"tag": "markdown", "content": "\n".join(meta_lines)}]
    if tags_md:
        left_elements.append({"tag": "markdown", "content": tags_md})

    score_str = str(score) if score else "—"
    rating_elements = [
        {
            "tag": "markdown",
            "content": f"## <font color='blue'>{score_str}</font>",
            "text_align": "center",
        },
        {
            "tag": "markdown",
            "content": (
                f"<font color='grey'>⭐ 评分</font>\n"
                f"<font color='grey'>({total}人 · 排名 #{rank or '-'})</font>"
            ),
            "text_align": "center",
            "text_size": "normal",
        },
    ]

    body_elements: list[dict] = [
        {
            "tag": "column_set",
            "flex_mode": "stretch",
            "horizontal_spacing": "12px",
            "horizontal_align": "left",
            "columns": [
                {
                    "tag": "column",
                    "width": "weighted",
                    "weight": 2,
                    "vertical_spacing": "8px",
                    "horizontal_align": "left",
                    "vertical_align": "top",
                    "elements": left_elements,
                },
                {
                    "tag": "column",
                    "width": "weighted",
                    "weight": 1,
                    "background_style": "blue-50",
                    "padding": "12px 12px 12px 12px",
                    "vertical_spacing": "2px",
                    "horizontal_align": "left",
                    "vertical_align": "top",
                    "elements": rating_elements,
                },
            ],
            "margin": "0px 0px 0px 0px",
        },
    ]

    if summary:
        s = summary if len(summary) <= summary_limit else summary[:summary_limit] + "…"
        body_elements.append({"tag": "markdown", "content": s, "margin": "0px 0px 0px 0px"})

    if img_key:
        body_elements.append(
            {
                "tag": "column_set",
                "horizontal_spacing": "8px",
                "horizontal_align": "left",
                "columns": [
                    {
                        "tag": "column",
                        "width": "weighted",
                        "weight": 1,
                        "vertical_align": "top",
                        "elements": [
                            {
                                "tag": "img",
                                "img_key": img_key,
                                "scale_type": "crop_center",
                                "size": "3:4",
                                "corner_radius": "8px",
                                "margin": "0px 0px 0px 0px",
                            }
                        ],
                    },
                    {
                        "tag": "column",
                        "width": "weighted",
                        "weight": 1,
                        "vertical_align": "top",
                        "elements": [],
                    },
                ],
                "margin": "0px 0px 0px 0px",
            }
        )
    return body_elements


def _title_subtitle(subject: dict) -> tuple[str, str]:
    name_cn = subject.get("name_cn") or ""
    name = subject.get("name") or ""
    title = name_cn or name or "(无名)"
    subtitle = name if (name_cn and name and name_cn != name) else ""
    return title, subtitle


def build_subject_detail_card(subject: dict, show_sub: bool = True) -> dict:
    """schema 2.0 条目详情卡片。左栏 meta + tags，右栏评分框；下方简介 + 半幅海报 + 按钮。

    show_sub=False 时隐藏「订阅更新」按钮（用于群聊场景，避免他人误触/未绑定）。
    """
    sid = subject.get("id")
    title, subtitle = _title_subtitle(subject)
    body_elements = build_subject_body_elements(subject)

    button_columns = [
        {
            "tag": "column",
            "width": "auto",
            "vertical_spacing": "8px",
            "horizontal_align": "left",
            "vertical_align": "top",
            "elements": [
                {
                    "tag": "button",
                    "text": {"tag": "plain_text", "content": "详情"},
                    "type": "primary_filled",
                    "width": "default",
                    "behaviors": [
                        {
                            "type": "open_url",
                            "default_url": f"https://bgm.tv/subject/{sid}",
                            "pc_url": "",
                            "ios_url": "",
                            "android_url": "",
                        }
                    ],
                    "margin": "4px 0px 4px 0px",
                }
            ],
        },
        {
            "tag": "column",
            "width": "auto",
            "vertical_spacing": "8px",
            "horizontal_align": "left",
            "vertical_align": "top",
            "elements": [
                {
                    "tag": "button",
                    "text": {"tag": "plain_text", "content": "吐槽箱"},
                    "type": "default",
                    "width": "default",
                    "behaviors": [
                        {
                            "type": "open_url",
                            "default_url": f"https://bgm.tv/subject/{sid}/comments",
                            "pc_url": "",
                            "ios_url": "",
                            "android_url": "",
                        }
                    ],
                    "margin": "4px 0px 4px 0px",
                }
            ],
        },
    ]
    if show_sub:
        button_columns.append(
            {
                "tag": "column",
                "width": "auto",
                "vertical_spacing": "8px",
                "horizontal_align": "left",
                "vertical_align": "top",
                "elements": [
                    {
                        "tag": "button",
                        "text": {"tag": "plain_text", "content": "订阅更新"},
                        "type": "default",
                        "width": "default",
                        "behaviors": [
                            {
                                "type": "callback",
                                "value": {"action": "sub", "subject_id": sid},
                            }
                        ],
                        "margin": "4px 0px 4px 0px",
                    }
                ],
            }
        )
    body_elements.append(
        {
            "tag": "column_set",
            "flex_mode": "stretch",
            "horizontal_spacing": "8px",
            "horizontal_align": "left",
            "columns": button_columns,
            "margin": "0px 0px 0px 0px",
        }
    )

    return {
        "schema": "2.0",
        "config": {"update_multi": True},
        "body": {"direction": "vertical", "elements": body_elements},
        "header": {
            "title": {"tag": "plain_text", "content": title},
            "subtitle": {"tag": "plain_text", "content": subtitle},
            "template": "blue",
            "padding": "12px 8px 12px 8px",
        },
    }


_COLL_STATUS = {1: "想看", 2: "看过", 3: "在看", 4: "搁置", 5: "抛弃"}


def _callback_button(
    content: str,
    value: dict,
    btn_type: str = "default",
    disabled: bool = False,
) -> dict:
    return {
        "tag": "button",
        "text": {"tag": "plain_text", "content": content},
        "type": btn_type,
        "width": "default",
        "disabled": disabled,
        "behaviors": [{"type": "callback", "value": value}],
        "margin": "4px 0px 4px 0px",
    }


def _wrap_buttons_row(buttons: list[dict]) -> dict:
    return {
        "tag": "column_set",
        "flex_mode": "stretch",
        "horizontal_spacing": "8px",
        "horizontal_align": "left",
        "columns": [
            {
                "tag": "column",
                "width": "auto",
                "vertical_spacing": "8px",
                "horizontal_align": "left",
                "vertical_align": "top",
                "elements": [b],
            }
            for b in buttons
        ],
        "margin": "0px 0px 0px 0px",
    }


def build_collection_detail_card(
    subject: dict,
    coll_type: str,
    page: int,
    user_collection: dict | None = None,
    back: str = "list",
    parent_id: int | None = None,
) -> dict:
    """列表页 → 点编号 → 条目详情。底部五按钮：简介 / 关联 / 点格子 / 返回 / 收藏管理。

    back="relations" + parent_id：用于从「关联」下钻进来的子条目，返回时回到上级的关联页。
    """
    sid = subject.get("id")
    stype = subject.get("type")
    title, subtitle = _title_subtitle(subject)
    body_elements = build_subject_body_elements(subject)

    if user_collection:
        status = _COLL_STATUS.get(int(user_collection.get("type") or 0), "—")
        ep_done = int(user_collection.get("ep_status") or 0)
        eps = subject.get("eps") or subject.get("total_episodes") or "?"
        rate = int(user_collection.get("rate") or 0)
        rate_str = f"⭐ {rate}/10" if rate else "⭐ 未评分"
        body_elements.insert(
            0,
            {
                "tag": "markdown",
                "content": f"**你的收藏** ：🏷 {status} · 📖 {ep_done}/{eps} · {rate_str}",
                "margin": "0px 0px 4px 0px",
            },
        )

    payload = {
        "subject_id": sid,
        "type": coll_type,
        "page": page,
    }
    if back == "relations" and parent_id is not None:
        payload["back"] = "relations"
        payload["parent_id"] = parent_id

    if back == "relations" and parent_id is not None:
        back_value = {"action": "relations", "subject_id": parent_id, "type": coll_type, "page": page}
    else:
        back_value = {"action": "page", "type": coll_type, "page": page}

    buttons = [
        _callback_button("简介", {"action": "summary", **payload}),
        _callback_button("关联", {"action": "relations", **payload}),
        _callback_button(
            "点格子",
            {"action": "eps", **payload},
            disabled=stype not in (2, 6),
        ),
        _callback_button("返回", back_value),
        _callback_button(
            "收藏管理",
            {"action": "edit", "subject_id": sid, "type": coll_type, "page": page},
            btn_type="primary_filled",
        ),
    ]
    body_elements.append(_wrap_buttons_row(buttons))

    return {
        "schema": "2.0",
        "config": {"update_multi": True},
        "body": {"direction": "vertical", "elements": body_elements},
        "header": {
            "title": {"tag": "plain_text", "content": title},
            "subtitle": {"tag": "plain_text", "content": subtitle},
            "template": "blue",
            "padding": "12px 8px 12px 8px",
        },
    }
