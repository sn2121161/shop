按成员最新指示，TTXL-4 改由 opencode 接管部署运维。成员已确认商城部署在腾讯云，并明确授权本轮通过 SSH 只读检查服务。

先读项目共享上下文、deploy/README.md、docs/understanding/operations.md，保留原报告。本次可运行：

```sh
ssh -o BatchMode=yes -o ConnectTimeout=15 -i ~/.ssh/tencent.pem ubuntu@106.55.2.188
```

远程目录 /srv/shop。使用有界远程命令同步采集结果，不启动后台进程；沿用 SSH 主机验证，不禁用 StrictHostKeyChecking。若主机未信任或认证失败，记录错误并停下，不改密钥/known_hosts/权限。私钥路径仅用于认证，不读取私钥内容。

只读检查：当前时间、/srv/shop 是否存在；deployed-sha 和 current 指向；Docker/Compose 项目、容器状态/健康、映射端口、镜像及 revision 标签；可用磁盘空间；备份文件数量/最近时间（不读备份正文）；对服务器本机 /health、/api/products、首页做有超时的 GET，仅输出状态或健康结果。使用受限 docker --format，禁止完整 inspect/config/env 输出，避免泄露凭证。若普通 docker 无权限，可尝试 sudo -n 的同类只读查询；失败即记录，禁止修改用户组或权限。不要查数据库业务行、真实 .env、私钥、日志正文或用户上传内容。

不得重启/停止服务、构建/部署、执行迁移、编辑服务器文件/权限/数据或重试发通知/提交真实运单。无需为了巡检重新发布。

将带查询时间的线上实测、与既有记录的差异、未验证项和接管结论简要写到 docs/understanding/server-opencode-check.md；仅能写这个本地文件，最终评论附文件，完成后 in_review；阻碍则 blocked 并说明。Mika 会汇总，opencode 不直接改项目共享提示词。
