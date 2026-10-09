# 后端

后端已迁移为 FastAPI。请先进入 `backend` 目录，所有 Python 命令均在 `firstenv` 中执行：

```bash
cd backend
conda run -n firstenv python -m pip install -r requirements.txt
conda run -n firstenv uvicorn app:app --reload --port 5600
conda run -n firstenv pytest
```

默认数据库 URL 为 `postgresql+psycopg2://postgres@localhost/nzw`：数据库名为 `nzw`，目标 schema 为 `shop`。如本机连接信息不同，设置 `DATABASE_URL` 后再启动。API 路径保持为 `/api`，默认服务地址为 `http://localhost:5600`。

后端采用分层结构：`shop_api/config.py` 管理配置，`database.py` 管理连接，`models.py` 放持久化模型，`schemas.py` 放请求校验模型，`security.py` 放认证与银行卡校验，`services.py` 放可复用业务服务，`routers.py` 按接口领域组织路由，`main.py` 只负责组装 FastAPI 应用。入口 `app.py` 仅为 Uvicorn 与测试保留。
