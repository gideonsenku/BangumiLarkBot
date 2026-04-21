import logging
import time

import requests

_BGM_API = "https://api.bgm.tv"
_BGM_NEXT_API = "https://api.bgm.tv/v0"
_BGM_OAUTH = "https://bgm.tv/oauth"
_UA = "BangumiFeishuBot/0.1 (https://github.com/)"

logger = logging.getLogger(__name__)


class BgmApiError(Exception):
    pass


class BgmApi:
    """Bangumi API 封装（同步 requests 版，足以应对 bot 量级请求）。"""

    def __init__(self, app_id: str, app_secret: str, callback_url: str, default_token: str = "") -> None:
        self.app_id = app_id
        self.app_secret = app_secret
        self.callback_url = callback_url
        self.default_token = default_token
        self._session = requests.Session()
        self._session.headers.update({"User-Agent": _UA})

    # ---------- OAuth ----------
    def _oauth_post(self, data: dict) -> dict:
        """bgm.tv 偶尔超时/502，这里做 2 次重试（指数退避）。"""
        last_exc: Exception | None = None
        for attempt in range(3):
            try:
                resp = self._session.post(
                    f"{_BGM_OAUTH}/access_token",
                    data=data,
                    timeout=20,
                )
                if resp.status_code >= 500:
                    raise BgmApiError(f"oauth {resp.status_code} {resp.text[:200]}")
                resp.raise_for_status()
                return resp.json()
            except (requests.Timeout, requests.ConnectionError, BgmApiError) as e:
                last_exc = e
                logger.warning("oauth_post attempt %d failed: %s", attempt + 1, e)
                if attempt < 2:
                    time.sleep(1 + attempt)
        assert last_exc is not None
        raise last_exc

    def oauth_authorization_code(self, code: str) -> dict:
        return self._oauth_post({
            "grant_type": "authorization_code",
            "client_id": self.app_id,
            "client_secret": self.app_secret,
            "code": code,
            "redirect_uri": self.callback_url,
        })

    def oauth_refresh_token(self, refresh_token: str) -> dict:
        return self._oauth_post({
            "grant_type": "refresh_token",
            "client_id": self.app_id,
            "client_secret": self.app_secret,
            "refresh_token": refresh_token,
            "redirect_uri": self.callback_url,
        })

    # ---------- User ----------
    def get_me(self, access_token: str) -> dict:
        resp = self._session.get(
            f"{_BGM_NEXT_API}/me",
            headers={"Authorization": f"Bearer {access_token}"},
            timeout=10,
        )
        resp.raise_for_status()
        return resp.json()

    # ---------- Collection ----------
    _SUBJECT_TYPE = {"book": 1, "anime": 2, "music": 3, "game": 4, "real": 6}
    _COLL_TYPE_DOING = 3  # 3=在看/在读/在玩

    def list_collection(
        self,
        bgm_user_id: int,
        coll_type: str,
        limit: int = 5,
        offset: int = 0,
        access_token: str | None = None,
    ) -> dict:
        """查询收藏列表。coll_type: book/anime/music/game/real"""
        subject_type = self._SUBJECT_TYPE[coll_type]
        headers = {}
        token = access_token or self.default_token
        if token:
            headers["Authorization"] = f"Bearer {token}"
        resp = self._session.get(
            f"{_BGM_NEXT_API}/users/{bgm_user_id}/collections",
            params={
                "subject_type": subject_type,
                "type": self._COLL_TYPE_DOING,
                "limit": limit,
                "offset": offset,
            },
            headers=headers,
            timeout=10,
        )
        resp.raise_for_status()
        return resp.json()

    def get_collection(self, subject_id: int, access_token: str) -> dict:
        """查询当前用户对单个条目的收藏状态。未收藏返回 {} 或 404。"""
        resp = self._session.get(
            f"{_BGM_NEXT_API}/users/-/collections/{subject_id}",
            headers={"Authorization": f"Bearer {access_token}"},
            timeout=10,
        )
        if resp.status_code == 404:
            return {}
        resp.raise_for_status()
        return resp.json()

    def update_coll_type(self, subject_id: int, coll_type: int, access_token: str) -> None:
        """修改收藏类型：1=想看 2=看过 3=在看 4=搁置 5=抛弃。"""
        resp = self._session.patch(
            f"{_BGM_NEXT_API}/users/-/collections/{subject_id}",
            headers={"Authorization": f"Bearer {access_token}"},
            json={"type": coll_type},
            timeout=10,
        )
        if resp.status_code >= 400:
            raise BgmApiError(f"update_coll_type {resp.status_code} {resp.text}")

    def update_ep_status(self, subject_id: int, ep_status: int, access_token: str) -> None:
        """仅用于书籍（subject_type=1），动画/剧集需改用 patch_episodes。"""
        resp = self._session.patch(
            f"{_BGM_NEXT_API}/users/-/collections/{subject_id}",
            headers={"Authorization": f"Bearer {access_token}"},
            json={"ep_status": ep_status},
            timeout=10,
        )
        if resp.status_code >= 400:
            raise BgmApiError(f"update_ep_status {resp.status_code} {resp.text}")

    def list_episodes(
        self,
        subject_id: int,
        ep_type: int = 0,
        limit: int = 200,
        offset: int = 0,
    ) -> dict:
        """ep_type: 0=本篇 1=SP 2=OP 3=ED"""
        resp = self._session.get(
            f"{_BGM_NEXT_API}/episodes",
            params={
                "subject_id": subject_id,
                "type": ep_type,
                "limit": limit,
                "offset": offset,
            },
            timeout=10,
        )
        resp.raise_for_status()
        return resp.json()

    def patch_episodes(
        self,
        subject_id: int,
        episode_ids: list[int],
        ep_type: int,
        access_token: str,
    ) -> None:
        """批量标记章节：ep_type 0=未收藏 1=想看 2=看过 3=抛弃。"""
        if not episode_ids:
            return
        resp = self._session.patch(
            f"{_BGM_NEXT_API}/users/-/collections/{subject_id}/episodes",
            headers={"Authorization": f"Bearer {access_token}"},
            json={"episode_id": episode_ids, "type": ep_type},
            timeout=10,
        )
        if resp.status_code >= 400:
            raise BgmApiError(f"patch_episodes {resp.status_code} {resp.text}")

    def update_rate(self, subject_id: int, rate: int, access_token: str) -> None:
        resp = self._session.patch(
            f"{_BGM_NEXT_API}/users/-/collections/{subject_id}",
            headers={"Authorization": f"Bearer {access_token}"},
            json={"rate": rate},
            timeout=10,
        )
        if resp.status_code >= 400:
            raise BgmApiError(f"update_rate {resp.status_code} {resp.text}")

    # ---------- Search / Subject / Calendar ----------
    def search(self, keyword: str, limit: int = 10) -> dict:
        resp = self._session.post(
            f"{_BGM_NEXT_API}/search/subjects",
            params={"limit": limit, "offset": 0},
            json={"keyword": keyword},
            timeout=10,
        )
        resp.raise_for_status()
        return resp.json()

    def get_subject(self, subject_id: int) -> dict:
        resp = self._session.get(f"{_BGM_NEXT_API}/subjects/{subject_id}", timeout=10)
        resp.raise_for_status()
        return resp.json()

    def get_subject_related(self, subject_id: int, access_token: str | None = None) -> list:
        headers = {}
        token = access_token or self.default_token
        if token:
            headers["Authorization"] = f"Bearer {token}"
        resp = self._session.get(
            f"{_BGM_NEXT_API}/subjects/{subject_id}/subjects",
            headers=headers,
            timeout=10,
        )
        resp.raise_for_status()
        return resp.json()

    def list_user_episode_collections(
        self,
        subject_id: int,
        access_token: str,
        offset: int = 0,
        limit: int = 100,
        episode_type: int = 0,
    ) -> dict:
        """章节 + 当前用户观看状态。未绑定/未收藏时调用方应退化到 list_episodes。"""
        resp = self._session.get(
            f"{_BGM_NEXT_API}/users/-/collections/{subject_id}/episodes",
            headers={"Authorization": f"Bearer {access_token}"},
            params={"offset": offset, "limit": limit, "episode_type": episode_type},
            timeout=10,
        )
        if resp.status_code == 404:
            return {"data": [], "total": 0, "limit": limit, "offset": offset}
        resp.raise_for_status()
        return resp.json()

    def patch_user_episode_collection(
        self,
        subject_id: int,
        episode_ids: list[int],
        status: int,
        access_token: str,
    ) -> None:
        """单集状态切换也走批量接口。status: 0=撤销 1=想看 2=看过 3=抛弃。"""
        if not episode_ids:
            return
        resp = self._session.patch(
            f"{_BGM_NEXT_API}/users/-/collections/{subject_id}/episodes",
            headers={"Authorization": f"Bearer {access_token}"},
            json={"episode_id": episode_ids, "type": status},
            timeout=10,
        )
        if resp.status_code >= 400:
            raise BgmApiError(f"patch_user_episode_collection {resp.status_code} {resp.text}")

    def calendar(self) -> list[dict]:
        """每日放送"""
        resp = self._session.get(f"{_BGM_API}/calendar", timeout=10)
        resp.raise_for_status()
        return resp.json()
