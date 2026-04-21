"""每日放送卡片。"""

_WEEKDAYS = {1: "一", 2: "二", 3: "三", 4: "四", 5: "五", 6: "六", 7: "日"}


def build_week_card(calendar: list[dict], weekday: int) -> dict:
    target = None
    for day in calendar:
        wid = (day.get("weekday") or {}).get("id")
        if wid == weekday:
            target = day
            break

    items = (target or {}).get("items", [])
    if not items:
        content = "_当日暂无放送数据_"
    else:
        lines = []
        for it in items[:20]:
            name = it.get("name_cn") or it.get("name") or "(无名)"
            sid = it.get("id")
            rating = (it.get("rating") or {}).get("score") or "-"
            lines.append(f"• **[{name}](https://bgm.tv/subject/{sid})** ⭐ {rating}")
        content = "\n".join(lines)

    return {
        "config": {"wide_screen_mode": True},
        "header": {
            "template": "violet",
            "title": {
                "tag": "plain_text",
                "content": f"📅 星期{_WEEKDAYS.get(weekday, '?')}放送",
            },
        },
        "elements": [
            {"tag": "div", "text": {"tag": "lark_md", "content": content}}
        ],
    }
