# Molecule Shop

面向分子主题饰品的全栈商城项目，包含用户商城、订单与配送、评论、管理员后台和经营看板。

## 技术栈

- 前端：React、Vinext、Ant Design、GSAP
- 后端：Python、FastAPI、SQLAlchemy
- 数据库：PostgreSQL（`shop` schema）
- 认证：JWT 与基于角色的管理员权限控制

## 项目结构

```text
shop/
├── backend/                 # FastAPI 服务与 PostgreSQL 数据模型
│   ├── app.py               # Uvicorn 入口
│   ├── shop_api/            # 路由、领域服务、模型与安全逻辑
│   └── tests/               # 后端测试
├── frontend/                # React / Vinext 用户端与管理端
│   └── app/                 # 页面、组件与全局样式
├── LICENSE
└── README.md
```

## 本地启动

### 1. PostgreSQL

默认连接地址为：

```text
postgresql+psycopg2://postgres@localhost/nzw
```

数据库使用 `shop` schema。如本地连接信息不同，请在 `backend/.env` 中设置 `DATABASE_URL`；不要提交该文件。

### 2. 后端

项目后端使用 Conda 环境 `firstenv`，默认端口为 `5600`：

```bash
cd backend
conda run -n firstenv python -m pip install -r requirements.txt
conda run -n firstenv uvicorn app:app --host 127.0.0.1 --port 5600 --reload
```

接口根路径为 `http://127.0.0.1:5600/api`，上传的商品及评论图片由 `/uploads` 提供。

### 3. 前端

需要 Node.js 22.13 或更高版本与 pnpm：

```bash
cd frontend
pnpm install
pnpm dev
```

前端开发服务器默认运行于 `http://localhost:3000`。

## 验证

```bash
# 后端
conda run -n firstenv python -m pytest backend/tests -q

# 前端
pnpm --dir frontend lint
pnpm --dir frontend build
```

## 许可证

本项目采用 [MIT License](LICENSE)。
