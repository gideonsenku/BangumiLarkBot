import hmac
import json
import logging
from concurrent.futures import ThreadPoolExecutor
from urllib.parse import urlencode

from flask import Flask, jsonify, redirect, render_template, request
from waitress import serve

from utils import feishu_client
from utils.config_vars import (
    API_AUTH_KEY,
    API_PORT,
    BGM_APP_ID,
    CALLBACK_URL,
    bgm,
    redis,
    sql,
)

logger = logging.getLogger(__name__)

app = Flask(__name__)
app.config["JSON_SORT_KEYS"] = False
app.config["JSONIFY_PRETTYPRINT_REGULAR"] = True

_executor = ThreadPoolExecutor(max_workers=2)


@app.route("/health")
def health():
    return "OK"


@app.route("/oauth_index")
def oauth_index():
    state = request.args.get("state")
    if not state:
        return render_template("error.html")
    if not redis.get(f"oauth:{state}"):
        return render_template("expired.html")
    url = "https://bgm.tv/oauth/authorize?" + urlencode(
        {
            "client_id": BGM_APP_ID,
            "response_type": "code",
            "redirect_uri": CALLBACK_URL,
            "state": state,
        }
    )
    return redirect(url)


@app.route("/oauth_callback")
def oauth_callback():
    code = request.args.get("code")
    state = request.args.get("state")
    if not code or not state:
        return render_template("error.html")
    data = redis.get(f"oauth:{state}")
    if not data:
        return render_template("expired.html")
    try:
        params = json.loads(data)
        open_id = params["open_id"]
        back = bgm.oauth_authorization_code(code)
        token_expires = 0
        if back.get("expires_in"):
            import time as _t
            token_expires = int(_t.time()) + int(back["expires_in"])
        sql.insert_user_data(
            open_id=open_id,
            bgm_user_id=int(back["user_id"]),
            access_token=back["access_token"],
            refresh_token=back["refresh_token"],
            token_expires=token_expires,
        )
        redis.delete(f"oauth:{state}")
        try:
            from feishubot.cards.common import build_bind_success_card
            feishu_client.send_card(open_id, build_bind_success_card(int(back["user_id"])))
        except Exception:
            logger.exception("send bind_success_card failed")
        return render_template("verified.html")
    except Exception:
        logger.exception("oauth_callback failed")
        return render_template("error.html")


_push_pool = ThreadPoolExecutor(max_workers=8)


def _push_one(open_id: str, card: dict) -> bool:
    try:
        feishu_client.send_card(open_id, card)
        return True
    except Exception:
        logger.warning("push card to %s failed", open_id)
        return False


def _normalize_items(req) -> list[dict]:
    """兼容三种入参：
    - GET/form 单条：?subject_id=&title=&volume=
    - POST JSON 单条：{"subject_id":..., "title":..., "volume":...}
    - POST JSON 批量：{"items":[{...},{...}]} 或裸 [ {...}, {...} ]
    """
    if req.is_json:
        body = req.get_json(silent=True)
        if isinstance(body, list):
            return body
        if isinstance(body, dict):
            if isinstance(body.get("items"), list):
                return body["items"]
            if body.get("subject_id"):
                return [body]
            return []
    sid = req.values.get("subject_id")
    if sid:
        return [{
            "subject_id": sid,
            "title": req.values.get("title", ""),
            "volume": req.values.get("volume", ""),
        }]
    return []


@app.route("/push", methods=["GET", "POST"])
def push():
    """订阅推送：支持批量。单次调用可携带任意条目 → 每条扇出到订阅者。

    鉴权：Content-Auth 头等于 config.API_SERVER.AUTH_KEY。
    """
    received = request.headers.get("Content-Auth") or ""
    if not hmac.compare_digest(received, API_AUTH_KEY):
        return jsonify({"code": 403, "message": "auth failed"}), 403

    items = _normalize_items(request)
    if not items:
        return jsonify({"code": 400, "message": "subject_id required"}), 400

    from feishubot.cards.push_notice import build_push_card

    total_ok, total_users = 0, 0
    results: list[dict] = []
    for item in items:
        raw_sid = item.get("subject_id")
        try:
            sid = int(raw_sid)
        except (TypeError, ValueError):
            results.append({"subject_id": raw_sid, "error": "invalid subject_id"})
            continue
        title = str(item.get("title") or "")
        volume = str(item.get("volume") or "")
        open_ids = sql.inquiry_subscribe_data(sid)
        if not open_ids:
            results.append({"subject_id": sid, "pushed": 0, "total": 0})
            continue
        card = build_push_card(sid, title, volume)
        futures = [_push_pool.submit(_push_one, oid, card) for oid in open_ids]
        ok = sum(1 for f in futures if f.result())
        results.append({"subject_id": sid, "pushed": ok, "total": len(open_ids)})
        total_ok += ok
        total_users += len(open_ids)

    return jsonify({
        "code": 200,
        "message": f"pushed {total_ok}/{total_users}",
        "results": results,
    })


def start_api() -> None:
    _executor.submit(lambda: serve(app, host="0.0.0.0", port=API_PORT))
    logger.info("api server listening on :%d", API_PORT)


def stop_api() -> None:
    _executor.shutdown(wait=False)
