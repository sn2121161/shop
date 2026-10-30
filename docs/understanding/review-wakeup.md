复核 TTXL-1 项目认知成果。先读取父任务及所有子任务状态，按运行规则扫描相关评论，再读取已交付的 docs/understanding/backend.md、frontend.md、operations.md。检查证据、未验证项和只读边界，并与 baseline-outside-docs.json 对照非 docs 跟踪文件内容。不要修改 docs 以外文件，不修复代码、不执行迁移/部署、不提交/推送/创建 PR、不读取真实密钥或业务数据。

如果三项均已交付，汇总更新 overview.md，将父任务设为 in_review，并通过唯一一条最终评论附报告交付。若仍有任务排队/执行，保留父任务 in_progress，交付本次确有的新结论，不重复分配，不轮询等待，不把部分交付说成全部完成。若某项阻碍，明确真实阻碍；超时唤醒也须核查当前状态，不自动重跑或改权限。done 留给成员。
