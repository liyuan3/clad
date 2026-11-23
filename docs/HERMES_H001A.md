# H001a — 第一批可独立验收任务

在 /home/fo/clad-hermes 的 hermes/backend-m1 分支执行。
先读 AGENTS.md 和 docs/CONTRACT.md。

本批只做：
1. FastAPI + SQLite 后端骨架。
2. 本地 CLI 创建用户，密码哈希；登录返回 token。
3. 设备配对码、到期、单次使用、每用户一台设备。
4. 会话创建/列表及历史消息读取。
5. 首页及 /static 服务 frontend 文件；路径用可配置项，不写死其他工作树路径。
6. 自动测试登录、配对过期/重用、A 用户不能读取 B 用户设备/会话。

不要做 Runner、支付或部署；不要修改 frontend 或接口契约。
写 docs/HERMES_REPORT.md，记录实现、测试命令、结果和未完成项。
提交本地分支；由 Codex 审查和推送。不要读取或输出密钥。

## 当前协作情况
Codex 已提交前端 9c38668，仅做过 JS 语法检查，尚未联调。
后台 Hermes 调用在文件修改确认处超时，未形成后端成果。
请在可交互 Hermes 终端执行本任务，并处理其正常修改确认。
