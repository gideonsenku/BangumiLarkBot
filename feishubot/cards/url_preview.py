"""飞书链接预览响应体。

- inline: 折叠态（链接旁的标题），必须有 title
- card: 展开态，type=card_json + data 为完整卡片 JSON
"""

from .subject_info import build_subject_card


def build_preview_response(subject: dict) -> dict:
    name = subject.get("name_cn") or subject.get("name") or "(无名)"
    rating = (subject.get("rating") or {}).get("score")
    eps = subject.get("eps") or subject.get("total_episodes")
    bits = [name]
    if rating:
        bits.append(f"⭐ {rating}")
    if eps:
        bits.append(f"{eps} 话")
    title = " · ".join(str(b) for b in bits)

    return {
        "inline": {"title": title},
        "card": {
            "type": "card_json",
            "data": build_subject_card(subject),
        },
    }


def build_preview_error(message: str = "预览加载失败") -> dict:
    return {"inline": {"title": message}}
