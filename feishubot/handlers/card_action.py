import logging
import math

from utils import feishu_client
from utils.config_vars import bgm, sql
from utils.user_token import TokenExpired, get_valid_token

from ..cards.collection_list import build_collection_card
from ..cards.common import build_error_card, build_need_bind_card
from ..cards.edit_collection import build_edit_collection_card
from ..cards.push_notice import build_push_card
from ..cards.subject_eps import EPS_PAGE_SIZE, build_eps_grid_card
from ..cards.subject_info import build_collection_detail_card, build_subject_detail_card
from ..cards.subject_relations import build_relations_card
from ..cards.summary import build_summary_card

logger = logging.getLogger(__name__)

PAGE_SIZE = 5


def handle_card_action(open_id: str, value: dict, message_id: str | None = None) -> None:
    """处理卡片按钮点击（在后台线程执行，返回值被 dispatcher 丢弃，故不再返回）。

    所有 UI 更新通过 `feishu_client.patch_card` 或 `send_card` 的副作用完成。
    """
    action = value.get("action")
    if action == "noop":
        return

    if action == "page":
        coll_type = value.get("type")
        page = max(1, int(value.get("page", 1)))
        _render_collection(open_id, coll_type, page, message_id)
        return

    if action == "ep_inc":
        subject_id = int(value["subject_id"])
        ep_status = int(value["ep_status"])
        ep_from = int(value.get("ep_from", max(0, ep_status - 1)))
        coll_type = value.get("type")
        page = int(value.get("page", 1))
        view = value.get("view")
        token_info = _get_token_or_bail(open_id)
        if not token_info:
            return
        try:
            _update_progress(subject_id, ep_from, ep_status, coll_type, token_info["access_token"])
        except Exception:
            logger.exception("update progress failed")
            feishu_client.send_card(open_id, build_error_card("更新进度失败，请稍后重试。"))
            return
        if view == "edit":
            _render_edit(open_id, subject_id, coll_type, page, message_id, token_info)
        else:
            _render_collection(open_id, coll_type, page, message_id)
        return

    if action == "edit":
        subject_id = int(value["subject_id"])
        coll_type = value.get("type")
        page = int(value.get("page", 1))
        token_info = _get_token_or_bail(open_id)
        if not token_info:
            return
        _render_edit(open_id, subject_id, coll_type, page, message_id, token_info)
        return

    if action == "rate":
        subject_id = int(value["subject_id"])
        rate = int(value["rate"])
        coll_type = value.get("type")
        page = int(value.get("page", 1))
        token_info = _get_token_or_bail(open_id)
        if not token_info:
            return
        try:
            bgm.update_rate(subject_id, rate, token_info["access_token"])
        except Exception:
            logger.exception("update_rate failed")
            feishu_client.send_card(open_id, build_error_card("更新评分失败，请稍后重试。"))
            return
        _render_edit(open_id, subject_id, coll_type, page, message_id, token_info)
        return

    if action == "coll_type":
        subject_id = int(value["subject_id"])
        new_type = int(value["coll_type"])
        coll_type = value.get("type")
        page = int(value.get("page", 1))
        token_info = _get_token_or_bail(open_id)
        if not token_info:
            return
        try:
            bgm.update_coll_type(subject_id, new_type, token_info["access_token"])
        except Exception:
            logger.exception("update_coll_type failed")
            feishu_client.send_card(open_id, build_error_card("更新状态失败，请稍后重试。"))
            return
        _render_edit(open_id, subject_id, coll_type, page, message_id, token_info)
        return

    if action == "detail":
        subject_id = int(value["subject_id"])
        in_group = bool(value.get("g"))
        try:
            subject = bgm.get_subject(subject_id)
        except Exception:
            logger.exception("get_subject failed")
            feishu_client.send_card(open_id, build_error_card("获取条目失败，请稍后重试。"))
            return
        card = build_subject_detail_card(subject, show_sub=not in_group)
        if message_id:
            try:
                feishu_client.patch_card(message_id, card)
                return
            except Exception:
                logger.warning("patch_card failed, fallback to send")
        feishu_client.send_card(open_id, card)
        return

    if action == "coll_detail":
        subject_id = int(value["subject_id"])
        coll_type = value.get("type") or "anime"
        page = int(value.get("page", 1))
        back = value.get("back") or "list"
        parent_id = value.get("parent_id")
        parent_id = int(parent_id) if parent_id is not None else None
        _render_coll_detail(open_id, subject_id, coll_type, page, message_id, back, parent_id)
        return

    if action == "summary":
        subject_id = int(value["subject_id"])
        coll_type = value.get("type") or "anime"
        page = int(value.get("page", 1))
        try:
            subject = bgm.get_subject(subject_id)
        except Exception:
            logger.exception("get_subject failed")
            feishu_client.send_card(open_id, build_error_card("获取条目失败，请稍后重试。"))
            return
        card = build_summary_card(subject, coll_type, page)
        _patch_or_send(open_id, message_id, card)
        return

    if action == "relations":
        subject_id = int(value["subject_id"])
        coll_type = value.get("type") or "anime"
        page = int(value.get("page", 1))
        try:
            subject = bgm.get_subject(subject_id)
            relations = bgm.get_subject_related(subject_id)
        except Exception:
            logger.exception("get relations failed")
            feishu_client.send_card(open_id, build_error_card("获取关联条目失败，请稍后重试。"))
            return
        card = build_relations_card(subject, relations or [], coll_type, page)
        _patch_or_send(open_id, message_id, card)
        return

    if action == "eps":
        subject_id = int(value["subject_id"])
        coll_type = value.get("type") or "anime"
        page = int(value.get("page", 1))
        ep_page = max(1, int(value.get("ep_page", 1)))
        _render_eps(open_id, subject_id, coll_type, page, ep_page, message_id)
        return

    if action == "ep_toggle":
        subject_id = int(value["subject_id"])
        ep_id = int(value["ep_id"])
        status = int(value.get("status", 2))
        coll_type = value.get("type") or "anime"
        page = int(value.get("page", 1))
        ep_page = max(1, int(value.get("ep_page", 1)))
        token_info = _get_token_or_bail(open_id)
        if not token_info:
            return
        try:
            bgm.patch_user_episode_collection(
                subject_id, [ep_id], status, token_info["access_token"]
            )
        except Exception:
            logger.exception("patch ep status failed")
            feishu_client.send_card(open_id, build_error_card("更新章节状态失败，请稍后重试。"))
            return
        _render_eps(open_id, subject_id, coll_type, page, ep_page, message_id, token_info=token_info)
        return

    if action == "sub":
        subject_id = int(value["subject_id"])
        user = sql.inquiry_user_data(open_id)
        if not user:
            feishu_client.send_card(open_id, build_need_bind_card())
            return
        if sql.check_subscribe(subject_id, open_id, None):
            sql.delete_subscribe_data(subject_id, open_id, None)
            feishu_client.send_text(open_id, f"已取消订阅 subject {subject_id}")
        else:
            sql.insert_subscribe_data(subject_id, open_id, user["bgm_user_id"])
            feishu_client.send_text(open_id, f"已订阅 subject {subject_id}")
        return

    if action == "unsub":
        subject_id = int(value["subject_id"])
        title = value.get("title", "")
        volume = value.get("volume", "")
        sql.delete_subscribe_data(subject_id, open_id, None)
        card = build_push_card(subject_id, title, volume, unsubscribed=True)
        if message_id:
            try:
                feishu_client.patch_card(message_id, card)
                return
            except Exception:
                logger.warning("patch_card failed, fallback to send")
        feishu_client.send_card(open_id, card)
        return

    logger.warning("unknown card action: %s", action)


def _update_progress(
    subject_id: int,
    ep_from: int,
    ep_to: int,
    coll_type: str | None,
    access_token: str,
) -> None:
    """书籍走 ep_status 字段；动画/剧集等按集标记已看/未看。"""
    if ep_to == ep_from:
        return
    if coll_type == "book":
        bgm.update_ep_status(subject_id, ep_to, access_token)
        return
    data = bgm.list_episodes(subject_id, ep_type=0, limit=200)
    episodes = data.get("data") or []
    episodes.sort(key=lambda e: (e.get("sort") or 0))
    lo, hi = (ep_from, ep_to) if ep_to > ep_from else (ep_to, ep_from)
    target_type = 2 if ep_to > ep_from else 0
    episode_ids = [e["id"] for e in episodes[lo:hi] if "id" in e]
    if not episode_ids:
        raise RuntimeError(f"no episodes to mark in range [{lo},{hi}) for subject {subject_id}")
    bgm.patch_episodes(subject_id, episode_ids, target_type, access_token)


def _get_token_or_bail(open_id: str) -> dict | None:
    try:
        token_info = get_valid_token(open_id, sql, bgm)
    except TokenExpired:
        feishu_client.send_card(open_id, build_error_card("Bangumi 授权已失效，请发送 `/start` 重新绑定。"))
        return None
    if not token_info:
        feishu_client.send_card(open_id, build_need_bind_card())
        return None
    return token_info


def _render_edit(
    open_id: str,
    subject_id: int,
    coll_type: str,
    page: int,
    message_id: str | None,
    token_info: dict,
) -> None:
    try:
        collection = bgm.get_collection(subject_id, token_info["access_token"])
    except Exception:
        logger.exception("get_collection failed")
        feishu_client.send_card(open_id, build_error_card("获取收藏状态失败，请稍后重试。"))
        return
    subject = collection.get("subject") or {}
    if not subject:
        try:
            subject = bgm.get_subject(subject_id)
        except Exception:
            logger.exception("get_subject failed (edit)")
            subject = {"id": subject_id}
    card = build_edit_collection_card(collection, subject, coll_type, page)
    if message_id:
        try:
            feishu_client.patch_card(message_id, card)
            return
        except Exception:
            logger.warning("patch_card failed, fallback to send")
    feishu_client.send_card(open_id, card)


def _patch_or_send(open_id: str, message_id: str | None, card: dict) -> None:
    if message_id:
        try:
            feishu_client.patch_card(message_id, card)
            return
        except Exception:
            logger.warning("patch_card failed, fallback to send")
    feishu_client.send_card(open_id, card)


def _render_coll_detail(
    open_id: str,
    subject_id: int,
    coll_type: str,
    page: int,
    message_id: str | None,
    back: str = "list",
    parent_id: int | None = None,
) -> None:
    try:
        subject = bgm.get_subject(subject_id)
    except Exception:
        logger.exception("get_subject failed")
        feishu_client.send_card(open_id, build_error_card("获取条目失败，请稍后重试。"))
        return
    user_collection: dict | None = None
    try:
        token_info = get_valid_token(open_id, sql, bgm)
    except TokenExpired:
        token_info = None
    except Exception:
        logger.exception("get_valid_token failed")
        token_info = None
    if token_info:
        try:
            user_collection = bgm.get_collection(subject_id, token_info["access_token"]) or None
        except Exception:
            logger.warning("get_collection (coll_detail) failed", exc_info=True)
            user_collection = None
    card = build_collection_detail_card(
        subject,
        coll_type=coll_type,
        page=page,
        user_collection=user_collection,
        back=back,
        parent_id=parent_id,
    )
    _patch_or_send(open_id, message_id, card)


def _render_eps(
    open_id: str,
    subject_id: int,
    coll_type: str,
    page: int,
    ep_page: int,
    message_id: str | None,
    token_info: dict | None = None,
) -> None:
    try:
        subject = bgm.get_subject(subject_id)
    except Exception:
        logger.exception("get_subject failed")
        feishu_client.send_card(open_id, build_error_card("获取条目失败，请稍后重试。"))
        return
    if token_info is None:
        try:
            token_info = get_valid_token(open_id, sql, bgm)
        except TokenExpired:
            token_info = None
        except Exception:
            logger.exception("get_valid_token failed")
            token_info = None

    offset = (ep_page - 1) * EPS_PAGE_SIZE
    user_mode = token_info is not None
    try:
        if user_mode:
            data = bgm.list_user_episode_collections(
                subject_id,
                token_info["access_token"],
                offset=offset,
                limit=EPS_PAGE_SIZE,
                episode_type=0,
            )
        else:
            data = bgm.list_episodes(
                subject_id, ep_type=0, limit=EPS_PAGE_SIZE, offset=offset
            )
    except Exception:
        logger.exception("list episodes failed")
        feishu_client.send_card(open_id, build_error_card("获取章节失败，请稍后重试。"))
        return

    eps_items = data.get("data") or []
    total = int(data.get("total") or len(eps_items))
    card = build_eps_grid_card(
        subject,
        eps_items,
        total=total,
        coll_type=coll_type,
        page=page,
        ep_page=ep_page,
        user_mode=user_mode,
    )
    _patch_or_send(open_id, message_id, card)


def _render_collection(open_id: str, coll_type: str, page: int, message_id: str | None) -> None:
    try:
        token_info = get_valid_token(open_id, sql, bgm)
    except TokenExpired:
        feishu_client.send_card(open_id, build_error_card("Bangumi 授权已失效，请发送 `/start` 重新绑定。"))
        return
    if not token_info:
        feishu_client.send_card(open_id, build_need_bind_card())
        return
    try:
        offset = (page - 1) * PAGE_SIZE
        data = bgm.list_collection(
            bgm_user_id=token_info["bgm_user_id"],
            coll_type=coll_type,
            limit=PAGE_SIZE,
            offset=offset,
            access_token=token_info["access_token"],
        )
    except Exception:
        logger.exception("list_collection failed")
        feishu_client.send_card(open_id, build_error_card("获取收藏失败，请稍后重试。"))
        return
    total = data.get("total", 0)
    total_pages = max(1, math.ceil(total / PAGE_SIZE))
    card = build_collection_card(data.get("data", []), page, total_pages, coll_type, total=total)
    _patch_or_send(open_id, message_id, card)
