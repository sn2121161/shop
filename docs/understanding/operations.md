# 部署认知：容器环境与 GitHub 发布现状

记录人：claude code（运维/部署专项）。日期：2026-10-30（Asia/Shanghai）。
任务：TTXL-4（父任务 TTXL-1）。本轮基线：本地 `dev` @ `e1259ea`（与 `origin/dev` 一致）。

**只读声明**：本轮未修改任何源码/配置/迁移文件，未构建镜像、未启动/停止/重启任何服务、未执行数据库迁移、未提交/推送、未创建 PR、未部署、未 SSH 登录服务器、未读取真实 `.env`/密钥/业务数据/日志正文。新增内容仅本文件。本地容器与 HTTP 探测均为只读命令（`docker ps/inspect/images/volume ls/compose ls`、GET 请求），GitHub 查询全部为 `gh` 只读命令。

## 0. 结论速览

1. 部署体系是一套「GitHub 测试 → 源码包 SSH 上传 → 服务器自建镜像 → 备份 → 迁移 → 切换 → 健康检查」的自动链路，仓库内定义完整，且 GitHub Actions 最近一次 main push（PR #10，2026-10-28）整条 deploy job 运行成功。
2. 本地开发栈（Colima/aarch64，3 容器）健康运行，但本地镜像为 arm64 且无构建元数据标签，不能视为生产镜像的同构副本；生产链路显式构建 amd64。
3. 生产服务器实际状态（容器、卷、备份、`deployed-sha`）本轮无法核实，文中所有服务器信息均为仓库文档的历史记录，已逐条标注。
4. 历史邮箱迁移已专项核对：`20261016_02` 为缺邮箱用户统一填默认邮箱（有 WHERE 限 NULL）；`20261017_03` 为**无 WHERE 的全表改写**，将所有用户邮箱按角色统一改写，且 downgrade 是反向全表改写。结合按邮箱找回密码的逻辑，这决定了账户找回的归属。生产是否已执行该迁移无法直接核实（间接线索见 §6）。

## 1. 部署相关文件清单（仓库定义）

| 文件 | 角色 | 要点 |
| --- | --- | --- |
| `backend/Dockerfile` | GitHub CI 后端构建定义 | `python:3.12-slim`，非 root `shop` 用户，uvicorn :5600 |
| `frontend/Dockerfile` | GitHub CI 前端构建定义 | `node:22-bookworm-slim` 两阶段；构建时读取 `.env.local` 后删除；运行 `vinext start` :3000 |
| `deploy/Dockerfile.api` | 服务器发布构建定义 | 基于 `shop-build-api:bootstrap`（首次从现有容器镜像固定），清空旧应用文件、保留 Python 包缓存，按 requirements 重装 |
| `deploy/Dockerfile.frontend` | 服务器发布构建定义 | 基于 `shop-build-frontend:bootstrap`，只保留 node_modules 缓存；构建时显式清掉 `NEXT_PUBLIC_API_URL/AMAP` 环境变量，以服务器 `.env.local` 为准 |
| `docker-compose.yml` | 本地三服务栈 | api(`127.0.0.1:5600`)/db(postgres:16, 无宿主端口, pg_isready 健康检查)/frontend(`0.0.0.0:3000`)；命名卷 `shop_postgres`、`shop_uploads`；均有 cpus/mem/pids 限制与 `restart: unless-stopped` |
| `docker-compose.production.yml` | 根目录覆盖文件 | 仅给 frontend 加 build arg `NEXT_PUBLIC_API_URL=/api`。注意：`frontend/Dockerfile` 未声明该 ARG，此覆盖当前不会产生实际效果（代码默认值本就是 `/api`，见 `frontend/app/shop.tsx:6,51`，无功能影响，属定义冗余） |
| `deploy/compose.yml` | 生产独立定义 | 项目名/卷名来自 `deploy.env`；`pull_policy: never`（缺镜像即停，不从远端拉）；api 仅绑 `127.0.0.1:5600`；frontend 绑 `${SHOP_FRONTEND_BIND:-127.0.0.1}:3000`；卷声明为 `external: true` |
| `deploy/deploy.sh` | 服务器发布总控（109 行） | 见 §3.2 |
| `deploy/build-on-server.sh` | 服务器构建+后端测试（68 行） | 见 §3.2 |
| `deploy/build-and-test.sh` | GitHub CI 构建+测试（58 行） | 见 §3.1 |
| `deploy/unpack-source.py` | 源码包安全解包 | 拒绝绝对路径/`..`/`.git`/`node_modules`/除 `.env.example` 外的 `.env*`/链接与特殊文件；解包目标必须是新建目录 |
| `deploy/server.env.example` | 服务器部署变量模板 | 项目名、应用 env 路径、前后端卷名、frontend 绑定地址、可选 pip/npm 国内镜像 |
| `.github/workflows/deploy.yml` | 唯一工作流「Test and deploy shop」 | 见 §3 |
| `tests/deployment/test_deploy.py` | deploy.sh 回归测试 | 用桩替换 docker/flock/curl，验证顺序与失败边界，不触 Docker |
| `tests/deployment/test_unpack_source.py` | 解包安全回归 | 正常源码/.env.example 放行；越界/绝对路径/链接/.env 拒绝 |
| `deploy/README.md` | 部署操作与配置文档 | 含生产服务器历史记录（见 §5） |
| `docs/tracking-webhook.md` | 物流订阅部署配置 | 含生产 deploy.env 记录与「已执行 20261027_04」记录（见 §5） |

`.gitignore` 排除 `.env`/`.env.*`/`deploy.env`/`*.pem`/`*.key`（保留 `.env.example`），`backend/.dockerignore` 排除 uploads 与缓存，`frontend/.dockerignore` 排除 `.env`/`.env.*` 但**显式放行 `.env.local`**（NEXT_PUBLIC_* 需在构建期烘焙进产物，两个 Dockerfile 构建后都执行 `rm -f /app/.env.local`，运行镜像不留该文件）。

## 2. 本地 Colima/Docker 环境实测（查询时间：2026-10-30 13:50–13:56 +08:00）

| 项 | 实测结果 |
| --- | --- |
| Colima | running，macOS Virtualization.framework，arch **aarch64**，runtime docker，mountType virtiofs，socket `~/.colima/default/docker.sock` |
| Docker | client 29.8.0 / server 29.5.2（API 1.54）；当前 context `colima`（另有 default、desktop-linux） |
| shop 容器 | `shop-api-1`（shop-api:local，up 3 days，`127.0.0.1:5600`）、`shop-db-1`（postgres:16，up 3 days **healthy**，无宿主端口映射）、`shop-frontend-1`（shop-frontend:local，up 2 days，`0.0.0.0:3000`） |
| Compose 项目 | `shop`，running(3)，config = 本仓库 `docker-compose.yml`；三个容器的 working_dir 标签均为本目录 |
| 命名卷 | `shop_shop_postgres`、`shop_shop_uploads` 存在（未读取内容） |
| 重启策略 | 三容器均 `unless-stopped`；db 健康检查 `pg_isready -U shop_prod -d shop_prod`（与 compose 定义一致） |
| 本地镜像 | shop-api:local 363MB（3 days 前）、shop-frontend:local 1.27GB（2 days 前）、postgres:16 663MB |
| 镜像架构 | 三者均为 **arm64/linux**；且两个 shop 镜像**没有** `org.opencontainers.image.revision` 标签 → 无法证明对应当前 `e1259ea` 提交，也不与生产 amd64 镜像同构 |
| 同机其他容器 | searxng（:8080）、n8n（:5678）与本仓库无关，仅登记避免混淆 |
| 只读 HTTP 探测 | `GET 127.0.0.1:5600/health` → 200；`GET localhost:3000/api/products` → 200；`GET localhost:3000/` → 200（仅状态码，未读取响应体） |

本地 git 状态：`dev` @ `e1259ea` 干净跟踪 `origin/dev`；本地 `main` 分支停在 `f6bf98d`（first commit，从未更新）；本地 `origin/main` 引用停在 `7f4ec1c`（≈PR #9 合并），落后远程当前 main `143a32f`（PR #10 合并）。本轮遵守只读约束**未执行 `git fetch`**，以上为本地引用快照。

## 3. 发布链路（仓库定义梳理）

### 3.1 触发与 CI（`.github/workflows/deploy.yml`，89 行）

- 触发：PR → `main`（只跑 build job）；push → `main` 与手动 `workflow_dispatch`（跑 deploy job，需 `github.ref == refs/heads/main`）。
- `permissions: contents: read`（不推镜像、不用 GHCR/Packages/artifact 存镜像）；并发组：PR 用分支名、其余固定 `production`，不取消进行中的运行（排队串行）。
- `environment: production`（GitHub 环境已存在，见 §4）。
- deploy job 流程：`deploy/build-and-test.sh` → `git archive "$GITHUB_SHA"` 打源码包（不含 `.git` 与未提交文件）→ 附带 compose.yml/deploy.sh/build-on-server.sh/unpack-source.py 并生成 `SHA256SUMS` → SSH 写入临时私钥（StrictHostKeyChecking=yes，退出时删除）→ rsync 上传（最多 3 次 × 10 分钟，`--partial --inplace` 断点续传）→ 远端 `sha256sum --check` 后执行 `deploy.sh DEPLOY_PATH shop-release <SHA>`。上传失败即退出，不替换运行中的服务。Secrets 校验含主机名/用户名/端口/路径的正则白名单。
- `deploy/build-and-test.sh`：先跑 `tests/deployment` unittest 回归 → `--platform linux/amd64` 构建前后端镜像（标签含 OCI revision = GITHUB_SHA）→ 前端镜像内跑 tsc + eslint，再以隔离容器做生产 SSR 探测（`/`、`/products/1`、`/cart`、`/tracking`、`/login`、`/register`、`/admin`，校验 200 且无 `__next_error__`）→ 后端镜像内以临时 Fernet key + SQLite 内存库跑 `pytest tests`。
- 注意：GitHub CI 用 `backend/Dockerfile`、`frontend/Dockerfile`；服务器发布用 `deploy/Dockerfile.*`。两套定义通过「基础镜像 bootstrap 固定 + OCI revision 标签校验」保持来源可追溯，升级基础镜像需专门维护 bootstrap 标签（deploy/README.md §服务器构建）。

### 3.2 服务器发布（`deploy/deploy.sh`，109 行 + `build-on-server.sh`，68 行）

顺序与失败边界：迁移前失败不会切换应用；迁移开始后数据库可能已变更，容器切换后的健康检查失败也不会自动回滚。各步骤如下：

1. `flock` 全局锁（等待上限 900s）+ source 服务器 `deploy.env`（部署参数与业务密钥分离，业务配置只存服务器 `.env`）。
2. 校验现有 db/api 容器存在、其实际挂载卷名与 `deploy.env` 配置一致 → **不会误建新库**；数据库容器全程保持运行。
3. SHA256 校验源码包 → `unpack-source.py` 安全解包到新目录。
4. `build-on-server.sh`：前端 `.env.local` 仅复制不执行（测试有命令注入用例），并拒绝指向 localhost/回环/Docker 服务名的 `NEXT_PUBLIC_API_URL`；bootstrap 基础标签缺失时从现有容器镜像 ID 一次性固定并断言 amd64；`--pull=false` 构建（不访问 Docker Hub），默认清华 PyPI + npmmirror；构建后在 `--network none` 隔离容器重跑后端 pytest。
5. 镜像校验：amd64 架构 + revision 标签 == 发布 SHA，记录镜像 ID。
6. 发布前配置校验（在 api 容器内）：`FRONTEND_URL`/`SMTP_*` 七项必填、`FRONTEND_URL` 必须公网 http(s)、SMTP 465 显式拒绝（当前邮件程序只支持 STARTTLS）、物流订阅参数完整性（订阅产品填了但商户 ID/密钥/回调不全则停止，避免静默切回手动查询）。
7. `pg_dump | gzip` 备份到 `<root>/backups/<UTC时间>-<SHA>.sql.gz`，`gzip -t` 校验后原子改名。**只备份数据库**，上传文件卷需人工备份。
8. 记录切换前镜像到 `previous-api-image.txt` / `previous-frontend-image.txt`（含首次部署）。
9. `alembic upgrade head`（迁移失败则不切换应用）。
10. `up -d --force-recreate --pull never api frontend`（force-recreate 同时让同 SHA 的服务器 env 修改生效）。
11. 健康检查 30 次 × 2s：`/health`、`/api/products`、`/`、`/products/1` 全过才算成功 → 写 `deployed-sha`、`current` 软链指向发布目录、删除源码 tar（保留解包源码/校验清单/镜像 ID/回滚记录）。失败则保留 tar 供排错，**新容器可能已在运行但不会自动还原数据库，也不会自动改写 `deployed-sha`**。

回滚（手动，仓库定义）：确认新库结构兼容旧代码后，在失败发布目录创建 `rollback.yml` 覆盖 api/frontend 镜像为 previous 记录，用 `SHOP_IMAGE_BASE=shop-release` + 原 compose.yml `up -d --pull never --force-recreate`。明确禁止 `down -v` 和自动 `alembic downgrade`（`20261017_03` 的 downgrade 本身就是全表改写，绝不可自动执行）。

## 4. GitHub 远程现状（查询时间：2026-10-30 13:51–13:55 +08:00，gh 只读）

- 仓库 `sn2121161/shop`：PUBLIC，默认分支 `main`，最近 push 2026-10-28T11:29:22Z。
- 远程分支仅 `dev`、`main`。`main...dev` 比较：dev 领先 0、落后 10 —— 落后部分是 10 个 PR 合并产生的 merge commit（只存在于 main），两分支内容树一致。
- PR 历史共 10 个，全部 `dev → main` 且全部 MERGED（#1 2026-10-10 → #10 2026-10-28）。#5「feature change deployment methods」、#6「deploy source changed and use ssh」对应发布链路两次重构，与 deploy/README 描述一致。
- **main 分支无分支保护**（API 404 "Branch not protected"）→ 任何有写权限者直接 push main 即触发生产部署流程，属治理风险点。
- Environment `production` 存在，无保护规则（无必需审批人，符合 deploy/README 的无人值守建议）；本次 deployment 对象查询返回 API 404，未取得对象；仅凭 404 无法证明历史上不存在 deployment，亦不能认定声明 environment 不会产生记录。发布结果以 Actions job 元数据为准。
- Actions Secrets：`DEPLOY_HOST`、`DEPLOY_USER`、`DEPLOY_SSH_KEY`、`DEPLOY_KNOWN_HOSTS` 四个全部存在（仅核名，值不可读也未读）；仓库 Variables 为空 → `DEPLOY_PORT`、`DEPLOY_PATH` 未配置，按工作流取默认值 `22`、`/srv/shop`（此为推断，非服务器事实）。
- 工作流状态 active，累计 17 次运行。按 main-push / dispatch 的 12 次（PR 构建运行全部成功）：

| 触发 | 时间 | 结论 | 备注 |
| --- | --- | --- | --- |
| push(PR#3 合并) | 10-22 09:48 | cancelled | 首个含迁移 02/03 的合并，部署未完成 |
| push(PR#4 合并) | 10-22 11:56 | cancelled | |
| workflow_dispatch | 10-22 14:06 | cancelled | |
| push(PR#5 合并) | 10-23 05:46 | **failure** | 旧「镜像传输」步骤失败（exit 1）；次日 #6 改为源码传输后成功 |
| push(PR#6 合并) | 10-24 16:05 | success | 首个全绿 deploy |
| push(PR#7 合并) | 10-27 05:25 | **failure** | 「Upload source over SSH and deploy」exit 255（SSH 类失败特征）；部署未完成 |
| push(PR#8 合并) | 10-27 06:37 | success | |
| push(PR#9 合并) | 10-27 07:37 | success | |
| push(PR#10 合并) | 10-28 11:29 | success | deploy job 11:29:28→11:57:16（约 28 分钟），当前 main `143a32f` |

边界声明：**workflow success ≠ 本轮核实了服务器状态**。绿色只能说明 GitHub 侧测试、上传与 deploy.sh 脚本自身全部通过（deploy.sh 设计上仅在健康检查通过后才写 `deployed-sha`），服务器实际容器/卷/备份状态仍属未知（§5）。运行详情来自 GitHub 元数据，未读取任何日志正文。

## 5. 生产部署状态：仓库文档记录 vs 已核实事实

以下全部为**仓库内的历史文档记录**，本轮未登录服务器，不能作为当前线上状态：

| 记录 | 出处 |
| --- | --- |
| 生产 Compose 项目名为 `app`（非模板的 `shop`），frontend 直接绑 `0.0.0.0:3000`，数据库/上传卷沿用现有安装 | deploy/README.md:115 |
| 服务器部署目录 `/srv/shop`，含 `deploy.env`、`backend/.env`、`frontend/.env.local`、`releases/`、`backups/`、`deployed-sha`、`current` | deploy/README.md §1/§4 |
| 生产 deploy.env 实际值记录：`SHOP_COMPOSE_PROJECT=app`、`SHOP_FRONTEND_ENV_FILE=/srv/shop/frontend/.env.local`、`SHOP_FRONTEND_BIND=0.0.0.0` | docs/tracking-webhook.md:48-52 |
| 公网商城地址 `http://106.55.2.188:3000`（HTTP，明文；文档自认未上 HTTPS，且与项目描述「腾讯云服务器」一致） | docs/tracking-webhook.md:9 |
| 「该服务器已执行 `20261027_04`」（物流订阅迁移） | docs/tracking-webhook.md:75 |
| 控制台回调校验已通过；真实运单订阅/受理/推送验收尚未完成 | docs/tracking-webhook.md §上线验收 |

**未核实（本轮无法核实）**：服务器容器是否仍在运行、`deployed-sha` 指向哪个提交、备份目录实际内容、磁盘占用与保留策略是否已建立、Apache/反代状态、真实邮件投递与真实运单推送是否验收通过。

## 6. 专项核对：历史邮箱迁移行为

代码事实（本轮逐行核对，与 deploy/README.md:119-121、根 README.md:194 的警示一致）：

- `20261016_02_user_email_password_resets.py:18`（upgrade）：仅对 `email IS NULL` 的行（有 WHERE），按角色统一填充——admin → 仓库内写死的 QQ 邮箱，其余用户 → 仓库内写死的 126 邮箱（地址见迁移源码，此处不转写）。同时加 email NOT NULL、`token_version`、`password_reset_tokens` 表和索引。
- `20261017_03_set_account_email_defaults.py:17-21`（upgrade）：**无任何 WHERE**，无条件将 `shop.users` 全表每个用户的 email 改写为上述角色默认值——任何用户自改的邮箱都会被覆盖，全部普通用户收敛到同一个 126 地址。downgrade（24-29 行）是**反向**全表改写（admin ↔ 普通用户互换默认地址），与 upgrade 不对称，同样会破坏数据。
- 与找回密码的耦合（`backend/shop_api/routers.py:64-76`）：按邮箱找回会把该邮箱匹配到的**所有** active 账号逐一生成重置链接发往同一邮箱 → 拥有该邮箱的人可重置全部匹配账号；全表统一后，普通账户的找回归属完全由仓库里写死的地址决定。注册侧（routers.py:45）校验邮箱唯一（409）→ 已被默认地址占用的邮箱无法再注册。
- 时间线（GitHub API 只读查询）：迁移 02/03 随 PR #3 于 2026-10-22 首次进入 main；该次及随后 PR #4 的 push 部署均 cancelled，PR #5 部署失败于上传步骤，**首个全绿部署是 PR #6（10-24 16:05 run 40109940345）**。alembic 逐版本升到 head，故若 10-24 部署真实完成且当时库中已有用户，迁移 02/03 已在生产执行；tracking-webhook.md:75「已执行 20261027_04」也以 02/03 已应用为前提——这两条均为**间接推断**，生产库当前实际邮箱分布未核实（不读生产数据）。
- 现状评估：该迁移作为「历史行为」不可在本认知任务中修复；其风险已被 deploy/README 与根 README 显式警示。需要人工决策的是：是否保留 03 的全表改写效果、`20261027_04` 之后新迁移务必带 WHERE 并避免触碰历史行为。** downgrade 绝不能在生产执行**（部署文档也已禁用自动 downgrade）。

## 7. 备份 / 迁移 / 健康检查 / 回滚能力小结

| 能力 | 仓库定义 | 状态 |
| --- | --- | --- |
| 数据库备份 | 每次发布迁移前自动 `pg_dump | gzip` 到 `/srv/shop/backups`，完整性校验；只备份数据库 | 定义存在；服务器实际备份是否在产生**未核实** |
| 数据库迁移 | 发布流程内 `alembic upgrade head`，失败即停；本地栈需手动执行（README §数据库 migration） | 定义存在；生产当前 alembic 版本未核实 |
| 健康检查 | GitHub 侧：SSR 七路径探测 + 隔离 pytest；服务器侧：`/health`、`/api/products`、`/`、`/products/1` 30×2s | 定义存在；失败不自动回滚，需人工查容器日志 |
| 回滚 | previous-*-image.txt + 手写 rollback.yml + 手动 compose up；禁 `down -v`/自动 downgrade；无数据库自动还原 | 定义存在；是否演练过未记录 |
| 部署锁定 | Actions 并发组排队 + 服务器 flock | 定义存在 |
| 停机窗口 | `--force-recreate` 切换，文档明示「不是零停机部署」 | 定义如此 |
| 磁盘治理 | 文档要求为备份/发布目录/构建缓存/旧镜像设保留策略，保留 bootstrap 标签与回滚镜像 | **仅有要求，未见自动化**，属待办风险 |

## 8. 未验证项与风险清单

1. **生产状态整体未知**（容器/卷/备份/deployed-sha/HTTPS），本轮无服务器访问权限（任务禁止 SSH）；§5 全部为文档记录。
2. **main 无分支保护** + push main 即部署：误推送即触发生产变更，建议后续加保护或启用环境审批（本任务不改配置）。
3. 部署非零停机；健康检查失败时新容器可能已替换旧容器且数据库已迁移，只能人工回滚应用、数据库回滚靠备份手工恢复。
4. `20261017_03` 全表改写的历史效果与 downgrade 风险（§6）。
5. 本地 `origin/main` 引用落后远程一个合并（未 fetch，遵守只读）；本地 main 分支本身从未更新，后续本地对比需依赖 gh 或先征得许可 fetch。
6. `docker-compose.production.yml` 的 build arg 与 `frontend/Dockerfile` 无 ARG 对接，覆盖文件当前无效（默认值恰好一致，暂无功能影响）。
7. GitHub 侧提示 `actions/checkout@v4` 走 Node 20 弃用强制升级、ubuntu-latest 将迁移 Ubuntu 26（runner-images#14748），未来构建环境变化需回归部署测试。
8. 部署测试（`tests/deployment`）是桩替身的逻辑回归，不能证明真实 SSH/rsync/服务器构建/PostgreSQL 并发行；SQLite 测试同理（与 overview.md §5 一致）。
9. 上传文件卷备份、磁盘保留策略无自动化（§7）。
10. 物流/邮件等外部集成：配置存在性由发布预检查校验，但真实投递/推送/额度未验收（文档自述）。

## 9. 证据与可复现命令

- 本地容器/镜像/卷：`colima status`、`docker version/context ls/ps/images/inspect/volume ls/compose ls`（只读，2026-10-30 13:50–13:56 +08:00）。
- 本地服务探测：`curl -o /dev/null -w '%{http_code}'` 三个 GET（13:53）。
- GitHub：`gh repo view / gh pr list / gh api repos/.../{branches,compare,commits,environments,actions/*}`、`gh run list/view`（13:51–13:55）。
- 迁移时间线：`gh api repos/sn2121161/shop/commits?path=<migration路径>&sha=main`。
- 仓库定义：§1 清单所列文件为本轮全文核对范围；未逐行审阅与本任务无关的前端/后端业务代码（归属 Pi/opencode 专项）。

## Mika 汇总复核补充

2026-10-30 复核时，以 gh 只读补查仓库 rulesets 返回空列表，与此前经典分支保护 404 证据合看，未发现当前仓库层面的 main 保护配置；该查询不修改远端设置。上文失败边界及 deployment 404 的表述已收窄，避免超出证据。
