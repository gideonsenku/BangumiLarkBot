import io
import json
import logging
import time

import lark_oapi as lark
import requests
from lark_oapi.api.im.v1 import (
    CreateImageRequest,
    CreateImageRequestBody,
    CreateMessageRequest,
    CreateMessageRequestBody,
    PatchMessageRequest,
    PatchMessageRequestBody,
    GetMessageResourceRequest,
)

from .config_vars import FEISHU_APP_ID, FEISHU_APP_SECRET

logger = logging.getLogger(__name__)

_client = (
    lark.Client.builder()
    .app_id(FEISHU_APP_ID)
    .app_secret(FEISHU_APP_SECRET)
    .log_level(lark.LogLevel.WARNING)
    .build()
)


def _require_ok(resp, action: str) -> None:
    if not resp.success():
        logger.error("feishu %s failed: code=%s msg=%s", action, resp.code, resp.msg)
        raise RuntimeError(f"feishu {action} failed: {resp.code} {resp.msg}")


def send_text(open_id: str, text: str) -> None:
    req = (
        CreateMessageRequest.builder()
        .receive_id_type("open_id")
        .request_body(
            CreateMessageRequestBody.builder()
            .receive_id(open_id)
            .msg_type("text")
            .content(json.dumps({"text": text}, ensure_ascii=False))
            .build()
        )
        .build()
    )
    resp = _client.im.v1.message.create(req)
    _require_ok(resp, "send_text")


def send_card(open_id: str, card: dict) -> str:
    """发送交互卡片，返回 message_id 便于后续 patch。"""
    req = (
        CreateMessageRequest.builder()
        .receive_id_type("open_id")
        .request_body(
            CreateMessageRequestBody.builder()
            .receive_id(open_id)
            .msg_type("interactive")
            .content(json.dumps(card, ensure_ascii=False))
            .build()
        )
        .build()
    )
    resp = _client.im.v1.message.create(req)
    _require_ok(resp, "send_card")
    return resp.data.message_id


def reply_card(chat_id: str, card: dict) -> str:
    req = (
        CreateMessageRequest.builder()
        .receive_id_type("chat_id")
        .request_body(
            CreateMessageRequestBody.builder()
            .receive_id(chat_id)
            .msg_type("interactive")
            .content(json.dumps(card, ensure_ascii=False))
            .build()
        )
        .build()
    )
    resp = _client.im.v1.message.create(req)
    _require_ok(resp, "reply_card")
    return resp.data.message_id


def reply_text(chat_id: str, text: str) -> None:
    req = (
        CreateMessageRequest.builder()
        .receive_id_type("chat_id")
        .request_body(
            CreateMessageRequestBody.builder()
            .receive_id(chat_id)
            .msg_type("text")
            .content(json.dumps({"text": text}, ensure_ascii=False))
            .build()
        )
        .build()
    )
    resp = _client.im.v1.message.create(req)
    _require_ok(resp, "reply_text")


def patch_card(message_id: str, card: dict) -> None:
    """更新已发送卡片（用于按钮点击后的异步刷新）。"""
    req = (
        PatchMessageRequest.builder()
        .message_id(message_id)
        .request_body(
            PatchMessageRequestBody.builder()
            .content(json.dumps(card, ensure_ascii=False))
            .build()
        )
        .build()
    )
    resp = _client.im.v1.message.patch(req)
    _require_ok(resp, "patch_card")


def download_image(message_id: str, file_key: str) -> bytes:
    req = (
        GetMessageResourceRequest.builder()
        .message_id(message_id)
        .file_key(file_key)
        .type("image")
        .build()
    )
    resp = _client.im.v1.message_resource.get(req)
    _require_ok(resp, "download_image")
    return resp.file.read()


def upload_image(data: bytes) -> str:
    """上传图片到飞书，返回 image_key。用于卡片内嵌图片（外链不渲染）。"""
    req = (
        CreateImageRequest.builder()
        .request_body(
            CreateImageRequestBody.builder()
            .image_type("message")
            .image(io.BytesIO(data))
            .build()
        )
        .build()
    )
    resp = _client.im.v1.image.create(req)
    _require_ok(resp, "upload_image")
    return resp.data.image_key


def get_client() -> lark.Client:
    return _client


_tenant_token: str = ""
_tenant_token_exp: float = 0.0
_bot_open_id: str = ""


def _get_tenant_token() -> str:
    global _tenant_token, _tenant_token_exp
    if _tenant_token and time.time() < _tenant_token_exp - 60:
        return _tenant_token
    resp = requests.post(
        "https://open.feishu.cn/open-apis/auth/v3/tenant_access_token/internal",
        json={"app_id": FEISHU_APP_ID, "app_secret": FEISHU_APP_SECRET},
        timeout=8,
    )
    resp.raise_for_status()
    data = resp.json()
    if data.get("code") != 0:
        raise RuntimeError(f"tenant_access_token: {data}")
    _tenant_token = data["tenant_access_token"]
    _tenant_token_exp = time.time() + data.get("expire", 7200)
    return _tenant_token


def get_bot_open_id() -> str:
    """获取机器人自身 open_id（懒加载 + 进程内缓存）。失败返回空串。"""
    global _bot_open_id
    if _bot_open_id:
        return _bot_open_id
    try:
        token = _get_tenant_token()
        resp = requests.get(
            "https://open.feishu.cn/open-apis/bot/v3/info",
            headers={"Authorization": f"Bearer {token}"},
            timeout=8,
        )
        resp.raise_for_status()
        data = resp.json()
        if data.get("code") != 0:
            raise RuntimeError(f"bot/v3/info: {data}")
        _bot_open_id = (data.get("bot") or {}).get("open_id") or ""
    except Exception:
        logger.exception("fetch bot open_id failed")
        _bot_open_id = ""
    return _bot_open_id
