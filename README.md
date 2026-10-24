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
