按成员最新指示，TTXL-2 改由 claude code 接管后端，Mika 在后端繁忙时协助。本轮交接认知，不是开发修复；之前由 Mika 接替 Pi 的技术报告保留。

先读项目共享上下文、docs/understanding/backend.md 和 backend/CONTEXT.md，核对 FastAPI/SQLAlchemy/Alembic 分层、firstenv/容器环境、15张表/38路由、JWT/重置密码、订单事务与模拟支付、通知和物流。确认已知邮箱迁移行为，区分测试定义与已验证事实。不要导入应用或启动服务，其初始化可能写目录/数据库及发送通知。

将接管确认、必要纠正、后端任务拆分与 Mika 协助方式简要写入 docs/understanding/backend-claude-handoff.md，最终评论附文件；完成后 in_review，done 留给成员。遇到任务积压或预计无法按期完成，在负责问题中说明可拆分的后端工作，交给 Mika 协调，避免共同改相同文件。

仅允许写该交接文件，不改其他项目文件，不安装/构建/测试/迁移/提交/推送/创建PR/部署，不读取真实环境文件、私钥或业务数据，不发送外部通知。后续业务修改须来自明确任务。
