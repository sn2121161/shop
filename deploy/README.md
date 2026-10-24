# GitHub Actions 自动部署

工作流：PR 到 `main` 时构建前后端并运行测试；合并或直接推送到 `main` 后，GitHub 再测试合并提交，然后通过 SSH 上传该提交的源码包，由服务器构建并测试发布镜像后部署。也可以在 Actions 页面手动运行（选择 `main`）。目标服务器须为 Linux x86_64。

不会自动提交、推送、合并代码。不会上传开发机 `.env`。上线可能有短暂中断，这不是零停机部署。

## 目录中的必要文件

| 文件 | 用途 |
|---|---|
| `build-and-test.sh` | GitHub 上构建镜像并运行测试 |
| `deploy.sh` | 服务器校验、备份、迁移、切换服务及健康检查 |
| `build-on-server.sh` | 服务器构建前后端并运行后端测试 |
| `unpack-source.py` | 检查并解压源码包 |
| `Dockerfile.api`、`Dockerfile.frontend` | 服务器构建定义，复用已有基础和依赖缓存 |
| `compose.yml` | 正式服务配置 |
| `server.env.example` | 服务器部署变量模板，不含密钥 |
| `README.md` | 配置及操作说明 |

部署回归测试位于 `tests/deployment/`，由 `build-and-test.sh` 自动运行。本地单独检查可执行 `python3 -m unittest discover -s tests/deployment -v`。

## 本次修改之后怎么操作

1. 本次已经验证服务器构建、后端测试和临时前端启动；正式服务尚未切换。先检查下文的邮箱 migration 提示，避免正式发布时覆盖用户邮箱。
2. 本地提交 Workflow、整个 deploy 目录、tests/deployment 及根 README.md 的变更，包括新增文件和旧测试路径的删除；不要提交任何 `.env`。
3. 将 `dev` 推送到 GitHub，创建或更新 `dev → main` 的 PR；等待 PR 测试通过后再合并。
4. 合并会自动创建一次新的 Test and deploy shop。无需手动再点 Run workflow，也不要重跑旧失败记录。
5. 新任务中应出现 Pack source at the tested commit、Upload source over SSH and deploy；服务器会构建、测试、备份和迁移后更新容器。GitHub 必须显示成功，再用浏览器检查首页、登录及忘记密码页面。实际发送重置邮件由你按需验收。

服务器沿用已有 `/srv/shop/deploy.env`、生产 `.env.production` 和四个 GitHub SSH Secrets。源码构建默认使用国内依赖源，无需再配置镜像仓库账号。保留服务器上 `shop-build-api:bootstrap`、`shop-build-frontend:bootstrap` 两个基础标签。

## 1. 在服务器准备一次

前提：现有 shop 的 db/api/frontend 已通过 Docker Compose 启动；部署账号可以直接运行 Docker，安装了 Compose v2、Python 3、Bash、curl、gzip、flock、rsync、sha256sum。SSH 必须能被 GitHub 托管 runner 访问。服务器需要能访问构建依赖镜像源，无需访问 GHCR；这里不接管 Apache、域名和证书配置。

以下示例部署目录是 `/srv/shop`，按实际路径替换。部署账号必须有写入权限。

```bash
mkdir -p /srv/shop/releases /srv/shop/backups
chmod 700 /srv/shop/backups
```

在现有项目目录运行以下只读命令，确定项目名称及持久卷，不要猜测：

```bash
docker compose ls
docker compose ps
docker inspect --format '{{ index .Config.Labels "com.docker.compose.project" }}' <现有API容器ID>
docker inspect --format '{{range .Mounts}}{{println .Destination .Name}}{{end}}' <现有数据库容器ID>
docker inspect --format '{{range .Mounts}}{{println .Destination .Name}}{{end}}' <现有API容器ID>
```

以 `deploy/server.env.example` 为参考，在服务器创建 `/srv/shop/deploy.env`：

```bash
SHOP_COMPOSE_PROJECT=shop
SHOP_ENV_FILE=/srv/shop/backend/.env
SHOP_DB_VOLUME=shop_shop_postgres
SHOP_UPLOAD_VOLUME=shop_shop_uploads
SHOP_FRONTEND_BIND=127.0.0.1
```

这里的示例值必须与现有容器匹配。`SHOP_ENV_FILE` 指向服务器已有的生产配置文件，也可以是 `/srv/shop/.env.production`。公网通过 Apache 反代时使用 `127.0.0.1`；若目前直接通过服务器 IP:3000 访问，需使用 `0.0.0.0`，否则会改变访问方式。

`deploy.env` 会被 Bash source，必须由可信的部署账号维护，只使用变量赋值。项目名和卷名必须保持不变。脚本发现不匹配会停止，不会自动创建空数据库。数据库容器保持运行，仅替换 api/frontend。

```bash
chmod 600 /srv/shop/deploy.env
chmod 600 /srv/shop/backend/.env
```

当前通过 SSH 传源码，不需要登录 GHCR、购买腾讯云镜像仓库或配置 REGISTRY_USERNAME/REGISTRY_PASSWORD。源码从 `git archive "$GITHUB_SHA"` 导出，与 GitHub 测试的是同一个提交，不包含未提交文件或 `.git` 历史。解包前校验 SHA256，并拒绝 `.env`、`node_modules`、链接和越界路径。服务器构建的镜像名称为 `shop-release-api:<提交SHA>` 和 `shop-release-frontend:<提交SHA>`。

### 服务器构建基础和依赖缓存

服务器第一次执行时，将现有 API、前端容器的镜像 ID 分别固定为 `shop-build-api:bootstrap`、`shop-build-frontend:bootstrap`。构建不重新拉取 Docker Hub 基础镜像，避免跨境下载。不要清理这两个标签。构建时清除旧应用文件，只保留已有 Python 包和前端 node_modules 缓存；再按 requirements 和 pnpm 锁文件安装依赖，复制新代码并重建前端。删除掉的旧路由不会残留。

服务器使用 `deploy/Dockerfile.api` 和 `deploy/Dockerfile.frontend`；GitHub 测试继续使用 backend/frontend 原有 Dockerfile。服务器构建后会再次运行隔离的后端测试，失败则不迁移、不切换容器。基础运行时版本继承首次固定的镜像；以后升级 Python、Node 或操作系统基础时，需要专门更新 bootstrap 标签和服务器构建文件，不能只修改 GitHub 使用的 Dockerfile。

默认 Python 包源为清华 PyPI 镜像，Node 包源为 npmmirror。可在服务器 `deploy.env` 中设置：

```bash
SHOP_PIP_INDEX_URL=https://pypi.tuna.tsinghua.edu.cn/simple
SHOP_NPM_REGISTRY=https://registry.npmmirror.com
```

构建时保留旧容器运行。前端构建限制 Node 堆内存约 1 GiB，构建命令设置 1536 MiB 内存参数；实际约束取决于 Docker 构建后端。服务运行资源限制仍由 Compose 管理。

## 2. 忘记密码的生产环境变量

`.gitignore` 继续忽略 `.env`，这是正确做法。只提交 `.env.example` 中的变量名和示例值。在服务器的 `SHOP_ENV_FILE` 文件中**追加或修改**下面这些变量，保留原来的数据库密码、JWT_SECRET、PAYMENT_ENCRYPTION_KEY 等配置；不要用本地 `.env` 整份覆盖生产配置。

```dotenv
FRONTEND_URL=http://你的服务器IP:3000
SMTP_HOST=你的SMTP服务器
SMTP_PORT=587
SMTP_USERNAME=你的QQ邮箱地址
SMTP_PASSWORD=邮箱SMTP授权码
SMTP_FROM=你的QQ邮箱地址
SMTP_STARTTLS=true
```

QQ 邮箱需要开启 SMTP 服务，`SMTP_PASSWORD` 使用邮箱生成的授权码。主机、端口与 TLS 方式以邮箱提供的配置为准，优先复用你本地已经验证可发信的 SMTP 设置。当前 `password_reset_email.py` 仅支持普通 SMTP + 可选 STARTTLS，**不支持 465 端口的隐式 SSL**；如果邮箱要求 465，需要先添加 SMTP_SSL 支持。

`FRONTEND_URL` 填浏览器实际访问商城的公网地址，支持 HTTP 或 HTTPS，例如 `http://你的服务器IP:3000`。不能照抄本地 localhost，否则邮件里的重置链接会指向用户自己的电脑。以后启用 HTTPS 时再更新这个值。部署会校验必填配置是否存在，但不会实际发信验证 SMTP 密码。

部署时 `--force-recreate` 会使新容器重新读取服务器 `.env`。如果只修改了服务器 `.env`，可以在 GitHub Actions 页面选择 `main` 手动重新运行完整工作流。生产配置只在服务器维护，不需要再放一份 SMTP_PASSWORD 到 GitHub Secrets。

### 合并前检查 migration

当前新增的 `20261017_03_set_account_email_defaults.py` 对 `shop.users` 执行无 WHERE 条件的 UPDATE，会将**全部普通用户邮箱改成同一个地址**，管理员也会被统一改写。前一条 `20261016_02` 也会为缺少邮箱的旧用户填入统一默认地址。这影响密码找回的归属；请在合并前确认或修正迁移。自动部署会真实执行这些 migration，不能只提交模型而遗漏迁移文件。

## 3. GitHub 配置

仓库 Settings → Environments → 创建 `production`，限制部署来源为 `main`。如果希望无人值守部署，不启用 Required reviewers。

Settings → Secrets and variables → Actions，添加以下 Repository secrets（也可添加到 `production` 的 Environment secrets）：

| 名称 | 值 |
|---|---|
| DEPLOY_HOST | 服务器 IPv4 或域名 |
| DEPLOY_USER | 已配置 SSH 公钥的部署账号 |
| DEPLOY_SSH_KEY | 对应专用 SSH 私钥的完整内容 |
| DEPLOY_KNOWN_HOSTS | 核实后的服务器 SSH host key 记录；非 22 端口使用 `[host]:port` 格式 |

`DEPLOY_KNOWN_HOSTS` 应从可信渠道取得并核对主机指纹，工作流启用严格主机验证。部署公钥放到服务器账号的 `~/.ssh/authorized_keys`。不要将个人 SSH 私钥或邮箱授权码提交 Git。

可选 Repository variables：`DEPLOY_PORT`（默认 `22`）、`DEPLOY_PATH`（默认 `/srv/shop`）。路径只支持 ASCII 字母、数字、下划线、连字符、斜杠。

工作流仅需 `contents: read`，不需要 `packages: write`。不使用 GitHub Packages 或 Actions artifact 存放镜像。GitHub Actions 自身的运行额度仍适用。

## 4. 发布和排错

你自行提交代码并合并到 `main` 后，在仓库 Actions 查看 `Test and deploy shop`。

发布顺序：GitHub 构建及测试 → `git archive` 导出提交源码并 gzip 压缩 → rsync 经 SSH 上传 → SHA256 校验 → 校验服务器配置/卷 → 安全解包 → 服务器构建前后端镜像 → 服务器后端测试 → 核对 amd64 架构和提交 SHA、记录镜像 ID → 校验邮件配置 → pg_dump 备份 → migration → 替换 api/frontend → API、前端代理和首页健康检查。

PR 构建任务上限为 30 分钟，main 的构建、测试、传输与部署任务总上限为 120 分钟。SSH 上传最多尝试 3 次，每次最多 10 分钟，网络中断后保留部分文件以便下一次尝试继续传输。全部文件校验通过后才会构建和部署。Compose 使用 `pull_policy: never` 和 `--pull never`，缺少发布镜像就停止，不会回退到远程仓库下载。

脚本仍接受 `ROOT IMAGE_BASE COMMIT_SHA` 三个参数，但必须与 `source.tar.gz`、`SHA256SUMS`、`compose.yml`、`build-on-server.sh`、`unpack-source.py` 一起放在发布目录中；不能拿旧镜像传输目录直接调用新版脚本。重跑工作流会生成新的发布目录，断点续传适用于同一任务中的上传重试。源码解包目录必须是新目录，不能在旧文件之上覆盖。

工作流串行部署，服务器还有 flock 锁。备份位于 `/srv/shop/backups`，成功版本记录在 `/srv/shop/deployed-sha`，`/srv/shop/current` 指向成功发布目录。成功后删除此次源码压缩包，保留解包源码、校验清单、镜像 ID 和回滚记录；失败时保留压缩包用于排错。首次上线前也应备份上传文件；脚本只自动备份数据库。备份、发布目录、构建缓存和旧镜像需要设置保留策略以免占满磁盘，并保留 bootstrap 基础标签与回滚镜像。

前端 Docker 构建就是当前前端校验；`pnpm test` 引用的 `tests/rendered-html.test.mjs` 在当前项目中不存在，暂未加入 CI。健康检查不代表邮箱投递成功，上线后需用自己的账号实测忘记密码流程。

迁移失败会停止切换应用。健康检查失败会把工作流标为失败，此时新容器可能已在运行，不会自动恢复数据库。到服务器查看对应 Compose 项目的容器日志（注意日志可能含业务信息）。每次发布目录会保存 previous-api-image.txt 和 previous-frontend-image.txt，记录切换前的镜像。

只有确认新数据库结构兼容旧代码后，才手动回滚应用。可在失败发布目录创建 `rollback.yml`，将上面记录的两个完整旧镜像名分别写入覆盖配置：

```yaml
services:
  api:
    image: 这里填previous-api-image.txt中的镜像
  frontend:
    image: 这里填previous-frontend-image.txt中的镜像
```

使用失败版本 SHA 和原发布目录（以下路径只是示例）执行：

```bash
set -a
source /srv/shop/deploy.env
set +a
export SHOP_IMAGE_BASE=shop-release
export SHOP_IMAGE_TAG=<失败发布的40位SHA>
docker compose --env-file /srv/shop/deploy.env \
  -f /srv/shop/releases/<发布目录>/compose.yml \
  -f /srv/shop/releases/<发布目录>/rollback.yml \
  up -d --no-deps --pull never --force-recreate api frontend
```

回滚后重新检查 API、页面、业务功能。不要执行 `down -v` 或自动 `alembic downgrade`。此脚本用于现有商城升级，首次建库和从备份恢复需要独立处理。
