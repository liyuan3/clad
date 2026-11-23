# H001b — 任务投递与可靠事件回传

Codex 已验收 H001a；42 pytest + 18 独立真实进程检查通过。
工作目录 /home/fo/clad-hermes，分支 hermes/backend-m1。先 git merge --ff-only main，同步最新契约和本任务。
范围仅 backend/、tests/、测试设备脚本及报告。不要修改 frontend/；不要接 Claude、不要做 Windows 安装包，不部署。保留 H001a 回归测试。

按顺序实现：
1. Run 和 RunEvent 持久化表。提供 CONTRACT 中 runs 创建/查询、events 游标查询、cancel 接口。用户归属校验覆盖全部接口。
2. /api/runner/ws：仅设备 Bearer token 可连接；心跳、超时下线、每设备唯一有效连接。旧连接断开不能把新连接设成 offline。
3. 在线闲置才接收新任务，设备忙碌/离线返回 409。一个设备仅一个未确认结束的任务，包括并发提交也不能突破。
4. 用户 request_id 唯一：同一请求重发返回原 run；同 id 不同会话或 prompt 返回 409；重复请求不能增加用户消息或重复投递。先查幂等记录，再查在线/忙碌状态。
5. run 及用户消息落库后才投递。投递失败/连接断开不能宣称没有执行；置 unknown 并保留设备占用，直到对账确认已停止。不能因断线就接新任务。
6. 事件按 (run_id,seq) 去重且持久化后 ACK。仅所属设备可写；seq 正整数、连续递增，重复同内容重发 ACK，冲突内容拒绝，跳号拒绝并报告期望序号。终态不可被后续事件改回 running。text 分块合并为一条 assistant 消息，终态只写一次。
7. cancel 是请求：只有 runner 确认 cancelled 才变已停止。终态取消返回已有状态，不重复产生消息。
8. 启动清理过期在线状态；中断任务进入 unknown，不自动重发 run。实现只报告状态的对账消息：runner 提供 run_id/status/last_seq，必须验证归属和状态迁移，不信任任意任务报告。先在 docs/HERMES_REPORT_H001B.md 写出协议增量及状态表，按最小保守方案实现，由 Codex 复核。
9. 本批 artifacts 列表接口可返回 []，不得伪称有文件；上传下载下批做。
10. 修正设备名纯空格可通过的问题，补回归测试。

验收必须包含：双用户隔离；设备 token 与用户 token 分离；并发两个提交只接一个；重复 request_id；断线/重连不重跑；重复事件不重复消息；乱序与跨设备事件拒绝；取消未确认不提前完成；同设备新旧连接交替关闭；真实进程重启后的 unknown 与保守对账。用测试 websocket 设备完成一轮文本回传，明确它不是 Claude 执行。

把运行命令、状态转换表、协议增量、测试数量和未完成项写 docs/HERMES_REPORT_H001B.md，不覆盖第一批报告。完成后仅本地提交，由 Codex 验收推送。有歧义先记录，不擅自扩大范围。
