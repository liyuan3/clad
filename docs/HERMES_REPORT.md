# Hermes report — backend M1 / H001a (batch 1)

Status: DONE（第一批，2026-11-23）。Runner、run/event、artifacts 按 H001a 要求未做，见“未完成项”。
分支：`hermes/backend-m1`（仅本地提交，由 Codex 审查后推送）。
契约：docs/CONTRACT.md 未修改；新增端点见“对契约的补充”，均为增量，不改变既有行为。

## 1. 本批实现

| 契约端点 | 状态 | 说明 |
|---|---|---|
| POST /api/auth/login | 已实现 | scrypt 哈希校验，返回 `{access_token,username}`；Bearer 会话表存 token 的 SHA-256，不存明文 |
| GET /api/devices | 已实现 | 只返回当前用户设备；`status` 为 online/offline/busy（本批恒为 offline，等待 runner 上线） |
| POST /api/devices/pairing | 已实现 | 8 位配对码（去掉 0/O/1/I），默认 10 分钟有效；同一用户新建即作废旧码 |
| POST /api/runner/pair | 已实现 | 配对码消费：单次、到期拒绝、每用户仅一台（DB 唯一约束 + 409） |
| GET /api/conversations | 已实现 | 按创建时间倒序，仅本人 |
| POST /api/conversations | 已实现 | 校验 device 归属，非本人设备返回 404 |
| GET /api/conversations/{id}/messages | 已实现 | 越权与不存在统一 404，不泄露存在性 |
| GET / | 已实现 | 返回 `CLAD_FRONTEND_DIR` 下的 index.html |
| GET /static/* | 已实现 | 静态资源；前端目录缺失时 503/404，进程不崩 |

代码结构（均为新文件）：

- `backend/app.py` — 应用工厂 `create_app(settings, init_db)`，路由挂载、静态托管、`/api/health`
- `backend/config.py` — 全部走环境变量：`CLAD_DATABASE_URL`、`CLAD_FRONTEND_DIR`、`CLAD_SESSION_TTL_SECONDS`、`CLAD_PAIRING_TTL_SECONDS`；不写死任何工作树路径
- `backend/db.py` — SQLite 引擎（WAL + foreign_keys）、`Database.session()`（CLI/测试用，退出即提交）
- `backend/models.py` — users / auth_sessions / devices / pairing_codes / conversations / messages；时间戳统一 naive UTC + 输出加 `Z`
- `backend/security.py` — scrypt 口令哈希（N=2^14,r=8,p=1，16MiB）、不透明 token、配对码生成/归一化
- `backend/deps.py` — `get_current_user`（用户 token）、`get_current_device`（设备 token）、`get_db`
- `backend/schemas.py` — 请求/响应模型与长度限制（口令上限 1024 防 scrypt DoS）
- `backend/cli.py` — `init-db` / `create-user` / `list-users` / `serve`；口令只从 getpass 或 stdin 读取，无默认账号、无注册接口
- `backend/routers/{auth,devices,conversations}.py`
- `tests/` — pytest 用例 + `tests/smoke_live.py`（真机 smoke 脚本，不进 pytest 收集）
- `pytest.ini`、`requirements.txt`

安全要点：口令 scrypt 加盐哈希；用户 token 与配对码只存哈希；配对码单次且可归一化输入；用户/设备凭据互相不可用（用户 token 打设备接口 401，反之亦然）；越权一律 404；用户名不存在时也跑一次 scrypt，避免时序差异泄露账号是否存在。

## 2. 启动与账号（Linux，本机已验证）

```bash
cd /home/fo/clad-hermes
python3 -m venv .venv
.venv/bin/pip install -r requirements.txt

# 初始化库（默认 data/clad.db，可用 CLAD_DATABASE_URL 覆盖）
.venv/bin/python -m backend.cli init-db

# 创建账号（无注册接口；口令交互输入或从 stdin 读一行，不落盘不回显）
.venv/bin/python -m backend.cli create-user --username alice
printf '%s\n' "$PASSWORD" | .venv/bin/python -m backend.cli create-user --username bob --password-stdin
.venv/bin/python -m backend.cli list-users

# 启动（CLAD_FRONTEND_DIR 默认取仓库根的 frontend/；前端在别的目录时必须显式配置）
.venv/bin/python -m backend.cli serve --host 127.0.0.1 --port 8000
# 前端目录不在本工作树时：
CLAD_FRONTEND_DIR=/home/fo/clad/frontend .venv/bin/python -m backend.cli serve --host 127.0.0.1 --port 8000
# 等价写法：
CLAD_FRONTEND_DIR=... .venv/bin/uvicorn backend.app:create_app --factory --host 127.0.0.1 --port 8000
```

默认配置（不设任何环境变量，DB 落 `data/clad.db`，前端取仓库 `frontend/`）也实测过：
`/api/health`、`/`、`/static/app.js`、`/static/style.css` 均 200。

Windows runner 启动命令属下一批（Runner 未实现），本批不给未经验证的命令。

## 3. 测试（真实执行结果）

```bash
cd /home/fo/clad-hermes
.venv/bin/python -m pytest
# 42 passed, 1 warning in 5.29s
#   tests/test_auth.py 12 / tests/test_pairing.py 12 / tests/test_conversations.py 12
#   tests/test_devices.py 3 / tests/test_static.py 3
```

覆盖点（对应 H001a 验收项）：

- 登录成功/失败；未知用户与错口令返回同一 detail；无 token、伪造 token、过期会话 401；`WWW-Authenticate: Bearer`
- 不存在注册接口（POST /api/auth/register → 404）；DB 内口令非明文、token 非明文
- 配对码形态与到期时间格式；到期拒绝；重复使用拒绝；新码作废旧码；未登录不能取码；码格式容错（小写/空格）
- 每用户一台：第二次配对 409，设备列表仍为 1；配对码归属人 = 设备归属人
- 设备 token 只能打 `/api/runner/device`，用户 token 不能打设备接口，设备 token 不能打用户接口
- 会话：创建/列表（倒序、按用户隔离）、用他人设备建会话 404、空白标题 422、未知会话 404
- 历史消息：空列表、按时间正序、角色正确、跨用户读取 404
- 静态：`/` 返回 index.html、`/static/app.js` 200、缺文件 404、无前端目录 503

真机 smoke（uvicorn + 真实 SQLite + 真实前端目录 `/home/fo/clad/frontend`）：

```bash
CLAD_DATABASE_URL=sqlite:////tmp/clad-smoke/clad.db CLAD_FRONTEND_DIR=/home/fo/clad/frontend \
  .venv/bin/python -m backend.cli serve --host 127.0.0.1 --port 8123
PYTHONPATH=. CLAD_DATABASE_URL=sqlite:////tmp/clad-smoke/clad.db \
  .venv/bin/python tests/smoke_live.py http://127.0.0.1:8123
# 18 项全部 PASS（health、/ 与静态资源、登录、配对、单次使用、设备自检、跨用户拒绝、二次绑定 409）
```

浏览器侧补充：打开 http://127.0.0.1:8123/ 前端登录弹窗正常渲染，无 console 错误，`/static/style.css`、`/static/app.js` 均 200。未在浏览器内输入真实口令（避免凭据进对话），登录链路由上面的 HTTP smoke 覆盖。

过程中发现并修复的真实缺陷：写操作原先只在依赖收尾时提交，而 FastAPI 在响应发出后才执行依赖 teardown，导致“创建配对码 → 立刻配对”在真实进程里读不到新码（pytest 里因为顺序不同没暴露）。现改为在 handler 内显式 `db.commit()`，`get_db` 只负责开关会话；修复后真机 smoke 通过。

## 4. 对契约的补充（未修改 CONTRACT.md）

1. `GET /api/health` → `{status,version}`，运维探活用。
2. `GET /api/runner/device` → `{id,name,status}`，设备凭据自检（runner 启动时验证 token 用；本批没有该端点则无法验证配对的返回值）。
3. `POST /api/runner/pair` 在本批实现（契约里已有），但仅做配对；websocket/run 仍属下一批。

以上均为增量，既有端点/字段未变。若 Codex 要求 `/api/runner/device` 去掉，可无损删除（仅测试引用）。

## 5. 未完成项（下一批）

- Runner（Windows/Claude adapter、参数数组、进程树取消、journal、重连回放）
- run / event / artifact / cancel 端点，websocket `/api/runner/ws`，服务器重启后 in-flight → unknown 的对账
- 设备在线状态维护（heartbeat）——当前恒为 offline
- 会话/设备注销、旧会话清理任务、登录速率限制（当前仅靠 scrypt 成本）
- M1 限制：单进程 + SQLite；多 worker 不支持（契约已声明），也不要跑 `--workers >1`

## 6. 限制与说明

- 上一轮中断的后台 Hermes 在工作树里留下了 3 个不可用的半成品文件（`backend/users.py` 引用不存在的 `config.MIN_PW_LEN`，`backend/serializers.py` 引用不存在的 `security.iso`，`backend/main.py` 为第二套入口）。它们无法 import、与本次实现重复，已删除，副本留在工作树外 `/tmp/clad-stale-backup/`（未提交）。如需保留 `uvicorn backend.main:app` 入口，请告知，我可按工厂写法补回。
- 未验证 Windows 行为（无 Windows 真机），上面所有结论均为 Linux + WSL 下真实进程验证，Windows/Claude 联调留给下一批。
- 用户名按精确匹配（大小写敏感），未做小写归一化。
- 未做 HTTPS/反向代理、CSRF（前后端同源、用 Bearer 而非 Cookie，故无 CSRF 面）。
- 仓库内无任何凭据；smoke 库在 `/tmp/clad-smoke/`，测试库在 pytest 临时目录，均未提交（`data/`、`*.db` 已在 .gitignore）。
