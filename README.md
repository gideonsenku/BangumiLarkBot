# Bangumi Feishu Bot

一个运行在飞书 / Lark 的 Bangumi 机器人，用于查询和管理你的番剧 / 书籍 / 游戏 / 音乐 / 剧集收藏。参考并移植自 [BangumiTelegramBot](https://github.com/bilahner/BangumiTelegramBot)。

## 功能

- 飞书自建应用 **WebSocket 长连**接入，无需公网 HTTPS 即可本地开发
- Bangumi OAuth 绑定 / 解绑
- 收藏查询（`/anime` `/book` `/game` `/music` `/real`）：编号翻页 → 点编号进入条目详情 → `简介 / 关联 / 点格子 / 返回 / 收藏管理`
- 条目搜索 `/search <关键字>`
- 每日放送 `/week [1-7]`
- 自动展开消息中的 Bangumi 条目链接
- 卡片内直接更新进度 / 评分 / 收藏状态
- OAuth 回调 + Redis 会话 + 事件幂等去重

## 交互流程（`/anime` 等收藏指令）

```
列表（编号 + 翻页）
   │
   ▼ 点击 ① ~ ⑤
条目详情（简介 | 关联 | 点格子 | 返回 | 收藏管理）
   ├── 简介     → 完整 summary
   ├── 关联     → 分组列出，点编号下钻到子条目详情
   ├── 点格子   → 章节网格，点编号切换"看过/撤销"
   └── 收藏管理 → 状态 / 评分 / 进度按钮
```

返回按钮会回到上一层；从关联下钻的子条目返回到关联页，再往上回到列表。

## 飞书应用配置

1. 打开 [飞书开放平台](https://open.feishu.cn/app)，创建「自建应用」。
2. 记录 **App ID** 和 **App Secret**。
3. 在「添加应用能力」启用「机器人」。
4. 「事件与回调」→「事件配置」选择 **「使用长连接接收事件」**。
5. 订阅事件：
   - `im.message.receive_v1` — 接收消息
   - `card.action.trigger` — 卡片按钮回调
6. 权限（最小集）：
   - `im:message`、`im:message:send_as_bot`
   - `im:resource`（图片下载）
7. 发布应用到组织 / 企业。

## 配置

复制模板：

```bash
cp .env.example .env
```

关键环境变量：

| 变量 | 说明 |
|------|------|
| `FEISHU_APP_ID` / `FEISHU_APP_SECRET` | 飞书自建应用凭据 |
| `FEISHU_TRANSPORT` | `websocket`（默认，推荐）或 `webhook` |
| `FEISHU_BOT_OPEN_ID` | 可选，填入后群聊可精准检测 @机器人 |
| `BGM_APP_ID` / `BGM_APP_SECRET` | Bangumi 应用凭据（用于 OAuth） |
| `BGM_ACCESS_TOKEN` | 可选；未绑定场景下调用 API 使用 |
| `API_PORT` | 本地 Flask 端口（默认 6008） |
| `API_WEBSITE_BASE` | Bangumi OAuth 回调必须可达；**生产必须是 HTTPS 公网地址** |
| `API_AUTH_KEY` | `/push` 推送接口鉴权头 |
| `REDIS_HOST` / `REDIS_PORT` / `REDIS_DB` | Redis 连接配置 |
| `LOG_LEVEL` | `DEBUG` / `INFO` / `WARNING` / `ERROR` |

> `.env` 已在 `.gitignore` 中，**不要提交到仓库**。容器环境可直接通过 `env_file` 或平台级变量注入，不一定需要物理 `.env`。

## 本地运行

需要 Python ≥ 3.10 和 Redis。

```bash
cp .env.example .env
# 编辑 .env 填入 FEISHU / BGM / API 的密钥

pip install -r requirements.txt
python main.py
```

私聊 bot 发送 `/help` 查看指令，或 `/start` 开始绑定。

## Docker Compose 运行

```bash
cp .env.example .env
# 编辑 .env 填入真实密钥。compose 会自动把 REDIS_HOST 覆写成 redis。

cd docker && docker compose up -d --build
docker compose logs -f bot
```

`docker/` 下的 compose 会把仓库根目录的 `data/` 挂载进容器（`../data:/app/data`），`bot.db` 和 `run.log` 留在宿主机；`.env` 通过 `env_file: ../.env` 注入。镜像内置了 `/health` 的 healthcheck。

## 指令列表

| 指令 | 说明 |
|------|------|
| `/start` | 绑定 Bangumi 账号 |
| `/unbind` | 解除绑定 |
| `/help` | 帮助 |
| `/anime` | 在看动画 |
| `/book` | 在读书籍 |
| `/game` | 在玩游戏 |
| `/music` | 在听音乐 |
| `/real` | 在看剧集 |
| `/search <关键字>` | 搜索条目 |
| `/week [1-7]` | 每日放送（空 = 今日） |
| `/info <id>` | 查看条目详情 |

## 架构

```
BangumiFeishuBot/
├── main.py                   # 启动入口
├── apiserver/                # Flask + waitress：OAuth 回调 / health / push
├── feishubot/
│   ├── bot.py                # lark.ws.Client 长连
│   ├── dispatcher.py         # 消息 / 卡片事件路由 + 幂等去重
│   ├── handlers/             # 每个指令 / 动作一个 handler
│   └── cards/                # 交互卡片 JSON 构造器
├── utils/                    # config / sqlite / bgm_api / user_token / feishu_client
├── data/                     # bot.db / run.log（运行期生成，不入库）
├── .env                      # 环境变量（不入库；参考 .env.example）
└── docker/                   # Dockerfile + docker-compose
```

## 贡献

Issue / PR 欢迎。提交前请确保：

- 不要把 `.env`、`data/*.db`、`data/*.log` 加入 commit
- 新交互请同步更新 README 的「交互流程」与「指令列表」

## 致谢

- [BangumiTelegramBot](https://github.com/bilahner/BangumiTelegramBot) — 原始实现与交互范式
- [Bangumi API](https://bangumi.github.io/api/) — 数据源
- [lark-oapi-python](https://github.com/larksuite/oapi-sdk-python) — 飞书 SDK

## License

[MIT](./LICENSE)
