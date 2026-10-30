# 线上巡检：腾讯云 /srv/shop（opencode 接管）

记录人：opencode（部署运维）。巡检时间：2026-10-30 15:07–15:09（Asia/Shanghai）。
任务：TTXL-4。基线文档：`deploy/README.md`、`docs/understanding/operations.md`（原报告保留，未改动）。

**只读声明**：本轮仅通过已授权 SSH 执行有界只读命令（`date`、`ls`/`readlink`/`find`/`stat`/`df`/`du`、受限 `docker ps|images|inspect --format|compose ls|system df|volume ls`、本机 `curl` GET）。未重启/停止服务、未构建/部署、未执行迁移、未改服务器文件/权限/数据、未运行 sudo、未读取 `.env`/私钥/日志正文/上传内容/数据库业务行。SSH 使用 `StrictHostKeyChecking=yes`，主机验证通过，未改动密钥或 known_hosts；私钥仅用于认证，未读取内容。本地仅新增本文件。

## 1. 结论速览

1. **生产在线，且与最新 main 一致**：`deployed-sha` = `143a32f6290ab326dfd3b053843b38fb04c36f6f`，`current` 指向该 SHA 的发布目录（run `40680345985`）；GitHub `main` 当前 SHA 与最近一次 main 运行（10-28，success）均为同一提交。
2. **三容器运行正常**：`app-api-1`、`app-frontend-1` 自 2026-10-28T11:57Z 发布切换后持续运行，重启次数 0；`app-db-1` 自 2026-10-11 起运行且 Docker 健康检查 `healthy`，项目 `app`、卷 `app_shop_postgres`/`app_shop_uploads` 与既有记录一致。
3. **服务可用**：服务器本机 GET `/health` → 200（`{"status":"ok"}`），`/api/products` → 200，首页 → 200，响应均在 20ms 内。
4. **磁盘尚可但有治理压力**：根分区 40G 已用 25G（67%），可用 13G；Docker 构建缓存 7.8GB 全部可回收，镜像 7.59GB 中 2.77GB 可回收。保留策略仍靠人工（与 operations.md §7 判断一致）。
5. **备份在产生**：`/srv/shop/backups` 共 10 个 `*.sql.gz`，最近一份为本次部署前 2026-10-28T11:56Z（7,835 字节），目录权限 700。仅登记数量/时间/大小，未读正文。
6. **接管结论**：线上状态与仓库文档、GitHub 记录相互吻合，未发现需要立即处置的异常；opencode 可继续承担只读巡检。重启、发布、迁移、权限或数据变更仍需单独授权。

## 2. 实测明细

| 项 | 实测结果（2026-10-30 15:07–15:09 +08:00） |
| --- | --- |
| 服务器时间 / 主机 | `2026-10-30T15:07:27+08:00`；`VM-0-3-ubuntu`；`uptime` 75 天，负载 0.08/0.03/0.03 |
| 登录身份 | `ubuntu`；普通 `docker` 命令可用，未使用 sudo |
| `/srv/shop` | 存在；顶层：`app`、`backend`、`backups`、`build-probes`、`current`、`deployed-sha`、`deploy.env`、`deploy.lock`、`.env.production`、`frontend`、`releases`、`transfer-probes` |
| `deployed-sha` | `143a32f6290ab326dfd3b053843b38fb04c36f6f` |
| `current` | 软链 → `/srv/shop/releases/143a32f6290ab326dfd3b053843b38fb04c36f6f-40680345985-1` |
| 发布目录 | `releases/` 共 15 个；含 10 个 `<SHA>-<run>-<n>` 自动目录与 5 个手工命名目录（`format-fix-*`、`validation-*`、`webhook-*`），合计 390MB |
| 当前发布目录内容（仅文件名） | `compose.yml`、`source`、`SHA256SUMS`、`api-image.id`、`frontend-image.id`、`previous-api-image.txt`、`previous-frontend-image.txt`、`deploy.sh`、`build-on-server.sh`、`unpack-source.py`；两份回滚记录均存在 |
| Compose 项目 | `app`，running(3)；配置标签：api/frontend → 当前发布目录 `compose.yml`；db → 旧的 `/srv/shop/app/docker-compose.yml` + `docker-compose.production.yml`（db 自 10-11 未重建，属发布脚本只替换 api/frontend 的设计） |
| 容器 | `app-api-1` Up 43h，`127.0.0.1:5600->5600/tcp`，重启 0，无 Docker healthcheck；`app-frontend-1` Up 43h，`0.0.0.0:3000->3000/tcp`，重启 0，无 Docker healthcheck；`app-db-1` Up 2 weeks **healthy**，仅容器网络 5432，重启 0；三者 `restart=unless-stopped` |
| 运行镜像 | api：`shop-release-api:143a32f…`，revision 标签 = `143a32f…`，`linux/amd64`；frontend：`shop-release-frontend:143a32f…`，revision 标签一致，`linux/amd64` |
| 数据卷 | `app_shop_postgres` → db `/var/lib/postgresql/data`；`app_shop_uploads` → api `/app/uploads`；均为命名卷 |
| 磁盘 | `/dev/vda2` 40G，已用 25G，可用 13G（67%）；`/srv/shop/releases` 390M、`backups` 84K、`app` 9.2M |
| Docker 占用 | 镜像 26 个（活跃 3）7.59GB，可回收 2.77GB；构建缓存 7.8GB（全部可回收）；卷 50.9MB 无回收项 |
| 备份 | 10 个 `*.sql.gz`；最近 `20261028T115647Z-143a32f….sql.gz`，7,835 字节；目录 `700 ubuntu` |
| 本机 HTTP | `127.0.0.1:5600/health` → 200（`{"status":"ok"}`，1.6ms）；`127.0.0.1:5600/api/products` → 200（19ms）；`127.0.0.1:3000/` → 200（7.9ms）；均设 10s 超时 |
| GitHub 对照（只读） | `main` = `143a32f…`；最近三次 main 运行为 #10/#9/#8 合并，均 success；#10 run `40680345985` 与发布目录名对应 |

## 3. 与既有记录的差异

1. **原报告「生产状态未知」已被本轮实测替代**：operations.md §5 中容器、`deployed-sha`、`current`、备份、卷名等原属「文档记录/未核实」，现已逐项与线上核对一致；原报告其余结论无需修改。
2. **卷名以项目名为前缀**：实际为 `app_shop_postgres` / `app_shop_uploads`。`deploy/README.md` 的 `shop_shop_*` 只是模板示例，不能套用到现有安装（文档本身已提示项目名为 `app`）；本轮确认部署脚本使用的卷与运行中 db 容器的实际挂载一致。
3. **`/srv/shop` 存在文档未列出的条目**：`app/`（旧 Compose 目录，db 容器仍沿用其配置标签）、`.env.production`、`build-probes/`、`transfer-probes/`、`deploy.lock`。本轮仅见文件名，未读取内容，用途未核实；`app/` 与 `.env.production` 是否为历史遗留需要后续确认，当前不影响运行。
4. **db 容器未随发布重建**：其 Compose 配置标签仍指向旧 `app/` 目录，api/frontend 指向当前发布目录。这与 deploy.sh 仅 `up api frontend` 的行为一致，不是异常；但也意味着 db 的 compose 定义变更不会自动生效。
5. **保留压力已量化**：15 个发布目录、26 个镜像、7.8GB 构建缓存，磁盘 67%。operations.md §7 的「保留策略仅有要求、未见自动化」在本轮得到数据印证；当前 13G 可用，不构成立即故障。
6. **`deployed-sha` 与 GitHub main 一致**：此前只能由 GitHub 绿色结果间接推断，本轮由服务器文件直接确认；发布目录名中的 run ID 也与 Actions 记录对应。

## 4. 未验证项

- 数据库实际 alembic 版本、表结构与业务数据（未连库、未查业务行）。
- `20261017_03` 邮箱全表改写在生产库中的实际影响（未读用户数据）。
- SMTP 真实投递、飞书通知、快递鸟订阅/回调的真实成功率与额度（仅确认服务进程在跑）。
- 公网访问链路：本轮只从服务器本机探测，未从外部验证 `http://106.55.2.188:3000`、域名、HTTPS、Apache/反代与防火墙状态。
- 前端浏览器端 hydration、交互与视觉（属 Pi 的前端专项）。
- 备份可恢复性（未做 restore 演练）、上传文件卷备份（脚本不覆盖）。
- 镜像/缓存/发布目录清理是否已按策略执行（当前仅确认可回收量）。
- 服务器安全更新、SSH 账户与登录来源（本轮未审计；`uptime` 显示 5 个登录会话，未展开）。

## 5. 接管结论与建议

- opencode 已可按授权方式（`ssh -i ~/.ssh/tencent.pem ubuntu@106.55.2.188`，严格主机校验）执行只读巡检；本轮未遇到权限或主机验证问题。
- 线上部署状态健康且可追溯到明确提交，发布链路产物（镜像 revision、`deployed-sha`、`current`、回滚记录、备份）齐全，接管无阻碍。
- 建议（均未执行，需另行授权）：为 Docker 构建缓存与旧镜像设定保留/清理策略；确认 `.env.production`、`app/`、`build-probes/`、`transfer-probes/` 的归属；补做一次备份恢复演练；评估 HTTPS/反代与外部可达性监控。
- 后续巡检可复用本轮命令集；任何重启、发布、迁移、权限或数据变更不得沿用「巡检」授权。
