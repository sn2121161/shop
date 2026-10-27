# Molecule Shop

面向分子主题饰品的全栈商城项目，包含用户商城、购物车、订单与配送、评论、管理员后台和经营看板。

## 技术与容器架构

- 前端：React、Vinext、Ant Design、GSAP
- 后端：Python、FastAPI、SQLAlchemy、Alembic
- 数据库：PostgreSQL 16（使用 `shop` schema）
- 认证：JWT 与基于角色的管理员权限控制
- 容器化：Docker Compose；本机 macOS 使用 Colima 提供 Docker runtime

Docker Compose 会启动三个服务：

```text
浏览器 http://localhost:3000
             │
             ▼
frontend（React / Vinext，3000）
  ├── /api/* ─────► api（FastAPI，5600）
  └── /uploads/* ─► api（上传图片）
                         │
                         ▼
                   db（PostgreSQL 16）
```

前端是唯一需要在浏览器直接访问的服务。API 仅绑定到本机 `127.0.0.1:5600`，数据库不暴露宿主机端口；前端通过容器网络转发 API 和上传文件请求。

## 项目结构

```text
shop/
├── backend/                 # FastAPI、Alembic migration 与后端测试
│   ├── app.py               # Uvicorn 入口
│   ├── migrations/          # 数据库版本迁移
│   └── shop_api/            # 路由、领域服务、模型与安全逻辑
├── frontend/                # React / Vinext 用户端与管理端
│   ├── app/                 # 页面、组件与全局样式
│   └── next.config.ts       # /api 与 /uploads 的容器内代理
├── docker-compose.yml       # 本地 Docker Compose 配置
├── docker-compose.production.yml
└── README.md
```

## 本地容器化启动（macOS）

所有命令都在项目根目录执行：

```bash
cd /Users/nzw/Documents/python_proj/shop
```

### 首次启动或代码更新后重建

```bash
# 1. 启动 Docker runtime
colima start

# 2. 构建镜像并启动数据库、API、前端
docker compose up -d --build

# 3. 应用数据库 migration（首次启动或新增 migration 后必须执行）
docker compose run --rm api alembic upgrade head

# 4. 查看服务状态
docker compose ps
```

启动完成后访问：

```text
商城：http://localhost:3000
API 健康检查：http://127.0.0.1:5600/health
```

### 日常启动

镜像未变更时可直接启动已有容器：

```bash
colima start
docker compose up -d
docker compose ps
```

### 查看日志与验收

```bash
# 持续查看全部日志
docker compose logs -f

# 仅查看某个服务
docker compose logs -f frontend
docker compose logs -f api
docker compose logs -f db

# 验证后端和商城接口
curl http://127.0.0.1:5600/health
curl http://localhost:3000/api/products
```

### 重启服务

```bash
# 重启全部服务
docker compose restart

# 仅重启前端或 API
docker compose restart frontend
docker compose restart api
```

### 停止服务

```bash
# 停止并删除容器、网络；保留 PostgreSQL 数据卷和上传文件卷
docker compose down

# 如不再使用容器运行时，再停止 Colima
colima stop
```

### 重置本地数据（危险操作）

以下命令会删除本地 PostgreSQL 数据和上传文件，无法恢复。只有需要从零开始时才执行：

```bash
docker compose down -v
```

## 高德自提点地图（个人学习 / 课程演示）

购物车选择「线下自提」后提供高德搜索、复制地址，以及可选的高德 JS API 2.0 内嵌地图。未配置 Key 时不会加载地图 SDK，仍可打开高德搜索；加载失败可重试。地图直接定位至已核对的高德门店记录「小行星桌游社·日麻·跑团」（POI `B0K6LDM3P4`，文化广场地下一层69号铺，GCJ-02 坐标 `119.972747,31.806285`），用红点和店名标签标记。该坐标于 2026-10-26 从高德地点搜索返回结果核对，不依赖每次打开页面重新搜索；如门店搬迁需更新坐标。

1. 在[高德控制台](https://console.amap.com/)创建「Web端（JS API）」Key 和对应安全密钥，并为 Key 设置实际使用的域名白名单。
2. 本机运行前端时，将 `frontend/.env.example` 复制为 `frontend/.env.local`，填写两个变量后重启或重新构建前端。
3. 使用 Docker Compose 时同样填写 `frontend/.env.local`，再执行 `docker compose up -d --build frontend`。无需根目录 `.env`，也无需额外指定 `--env-file`。构建读取该文件，配置变化会使构建缓存失效；原始配置文件不会保留在最终运行镜像中。
4. 使用服务器自动构建部署时，前端配置放在服务器 `/srv/shop/frontend/.env.local`，后端配置继续由 `SHOP_ENV_FILE` 指向（推荐 `/srv/shop/backend/.env`）。`deploy.env` 仅保存部署参数；如需自定义前端配置文件位置，可设置 `SHOP_FRONTEND_ENV_FILE`。前端配置变化后需要重新构建，不能只重启容器。

```dotenv
NEXT_PUBLIC_API_URL=/api
NEXT_PUBLIC_AMAP_KEY=你的Web端JS_API_Key
NEXT_PUBLIC_AMAP_SECURITY_JS_CODE=对应的安全密钥
```

此版本为个人课程演示，按高德文档的浏览器明文安全密钥方式接入，两个值都会出现在浏览器资源中，不应复用服务端密钥。正式上线应按[高德安全密钥文档](https://developer.amap.com/api/javascript-api-v2/guide/abc/jscode)改用服务端代理；商业用途和免费额度期限按[高德许可说明](https://lbs.amap.com/faq/advisory/authorization/43168)与账号控制台确认。本项目不会自动购买许可或调用包。

## 分子资料卡与快递查询

商品详情页展示 PubChem 分子结构参考图、分子式、分子量、系统命名、CID 与资料来源。目前核对了 13 个分子，数据和结构图保存在前端，本地展示不依赖访客访问 PubChem。THC、海洛因 I/II 型、迷幻剂等名称未限定具体结构时展示待确认说明，新建的未知商品同样不猜测分子数据。

手动更新资料（需要访问 PubChem，不需要 API Key）：

```bash
node frontend/scripts/sync-molecules.mjs
```

更新后重新构建前端。资料不是首饰材质或功效声明，薄荷醇卡片明确使用左旋薄荷醇作为结构参考。参考数据来源与更新日期保存在 `frontend/app/data/molecules.json`。

首页导航、页脚及非自提订单页提供 `/tracking` 站内物流轨迹查询。后端接入快递鸟，当前版本支持圆通、申通、极兔、百世，其他快递商提示暂未接入。接口指令通过 `backend/.env` 中的 `KDNIAO_REQUEST_TYPE` 指定，当前账号配置为已开通的快递查询 `8002`，保留 `1002` 的兼容支持。用户需登录；凭证仅配置于 `backend/.env` 的 `KDNIAO_EBUSINESS_ID` 与 `KDNIAO_API_KEY`。未开通时页面明确提示，运单号不写数据库，查询结果仅在内存缓存 5 分钟。申请入口、期限、额度及支持范围见 [免费物流服务与开通说明](docs/free-shipping-options.md)。

## 数据库 migration

当功能涉及数据表、字段或数据结构时：

1. 在 `backend/migrations/versions/` 创建并提交 Alembic migration。
2. 本地执行 `docker compose run --rm api alembic upgrade head`。
3. 部署服务器时也执行同一命令，再启动新版本 API 和前端。

不要手动修改生产数据库结构，也不要把 migration 文件遗漏在 Git 提交之外。

## 环境变量与数据文件

- 开发环境可参考 `backend/.env.example` 创建 `backend/.env`。
- `backend/.env`、生产环境 `.env.production`、JWT/加密密钥等敏感配置不得提交 Git。
- 通过管理后台上传的商品图片保存在 Docker volume 中，不会随 `git push` 同步；迁移环境时需要单独迁移 PostgreSQL 数据和上传文件卷。

## 验证与测试

登录会话由后端签发的 12 小时 JWT 保护。前端初始化时通过 `/api/auth/me` 核对已保存的会话；受保护接口返回 401 后，清除对应前台/管理员会话和页面登录状态，并跳转 `/login?reason=expired`。登录密码错误不触发过期跳转，多个并发过期请求只跳转一次，网络错误不会直接删除登录信息。

```bash
# 前端构建与 HTML 测试
pnpm --dir frontend test

# 后端测试（若本机配置了 Python 测试环境）
python -m pytest backend/tests -q
```

## GitHub 自动部署

合并到 `main` 后自动测试，通过 SSH 上传该提交的源码包，由服务器利用已有基础镜像和国内依赖源构建、测试后部署，无需传输完整镜像或访问 GHCR。首次使用前，按 [部署配置说明](deploy/README.md) 设置 GitHub Secrets 和服务器 `deploy.env`，并在服务器现有 `.env` 中补齐忘记密码邮件配置。工作流不会上传或覆盖本地/生产 `.env`。

当前新增 migration 会改写旧用户邮箱，合并前请阅读部署说明中的 migration 提示。

## 许可证

本项目采用 [MIT License](LICENSE)。

物流可另行开通订阅推送，首次登记单号后由快递鸟回调更新数据库，页面显示最新物流节点与本站同步时间。配置仍只放 `backend/.env`；参见 [物流订阅与回调](docs/tracking-webhook.md)。
