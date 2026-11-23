# CLAD
网页向绑定的 Windows / VM 下达需求，Claude Code 执行并持续回传结果。

当前阶段：M1 开发中，尚不可用于生产。

## 分工
- Codex：架构、接口契约、前端、验收。
- Hermes：后端、Windows Runner、自动化测试、运行说明。
- 协作记录：docs/HERMES_TASKS.md、docs/HERMES_REPORT.md；源码以 GitHub 分支提交为准。
- 原项目 /home/fo/clawproduct-hunt 仅作参考，不复制数据库、凭据、运行数据，不修改原项目。

## 首版范围
一平台用户绑定一台设备；设备每次执行一个任务。支持持续会话、执行事件、停止、重连查询、成果下载。离线拒绝新任务，忙碌返回冲突。暂不做交易、竞标、自更新和机器池调度。
