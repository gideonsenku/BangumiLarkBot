import os

import redis as redis_lib
from dotenv import load_dotenv

from .sqlite_orm import SqliteOrm
from .bgm_api import BgmApi

_PROJECT_ROOT = os.path.dirname(os.path.dirname(__file__))

# 允许在容器中通过 env_file / docker env 直接注入；本地开发从 .env 读取。
load_dotenv(os.path.join(_PROJECT_ROOT, ".env"))


def _required(key: str) -> str:
    val = os.environ.get(key, "").strip()
    if not val:
        raise RuntimeError(f"环境变量 {key} 未设置；请参考 .env.example 配置 .env")
    return val


LOG_LEVEL: str = os.environ.get("LOG_LEVEL", "INFO")

FEISHU_APP_ID: str = _required("FEISHU_APP_ID")
FEISHU_APP_SECRET: str = _required("FEISHU_APP_SECRET")
FEISHU_TRANSPORT: str = os.environ.get("FEISHU_TRANSPORT", "websocket")
BOT_OPEN_ID: str = os.environ.get("FEISHU_BOT_OPEN_ID", "")

BGM_APP_ID: str = _required("BGM_APP_ID")
BGM_APP_SECRET: str = _required("BGM_APP_SECRET")
BGM_ACCESS_TOKEN: str = os.environ.get("BGM_ACCESS_TOKEN", "")

API_PORT: int = int(os.environ.get("API_PORT", "6008"))
API_WEBSITE_BASE: str = _required("API_WEBSITE_BASE")
API_AUTH_KEY: str = _required("API_AUTH_KEY")

CALLBACK_URL: str = API_WEBSITE_BASE.rstrip("/") + "/oauth_callback"

REDIS_SESSION_EXPIRES: int = int(os.environ.get("REDIS_SESSION_EXPIRES", "86400"))

redis = redis_lib.Redis(
    host=os.environ.get("REDIS_HOST", "localhost"),
    port=int(os.environ.get("REDIS_PORT", "6379")),
    db=int(os.environ.get("REDIS_DB", "0")),
    decode_responses=True,
)

sql = SqliteOrm(os.path.join(_PROJECT_ROOT, "data", "bot.db"))

bgm = BgmApi(
    app_id=BGM_APP_ID,
    app_secret=BGM_APP_SECRET,
    callback_url=CALLBACK_URL,
    default_token=BGM_ACCESS_TOKEN,
)
