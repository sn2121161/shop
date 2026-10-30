# 后端接管确认：claude code

记录人：claude code。日期：2026-10-30，任务 TTXL-2，父任务 TTXL-1。
源码基线：dev，`e1259ea`（与 Mika 报告 `docs/understanding/backend.md` 相同基线）。

按成员指示，后端由 claude code 接管；Mika 在后端繁忙或任务积压时承接明确范围的协助。本文件是认知交接，不是开发修复；Mika 接替 Pi 完成的 `backend.md` 报告继续有效，本文件只补充接管确认、纠正与协作方式。

## 接管确认

已读项目共享上下文（`docs/understanding/project-shared-prompt.md`）、`docs/understanding/backend.md`、`backend/CONTEXT.md`，并对照源码逐项静态核对（只读 grep/读取，未导入应用、未运行测试/迁移/服务，未读真实 `.env`、密钥或业务数据）。

核对项全部与报告一致：

- **分层**：FastAPI 应用工厂 + lifespan 在 `shop_api/main.py`，配置 `config.py`，引擎/会话 `database.py`，ORM `models.py`，校验 `schemas.py`，认证 `security.py`，路由 `routers.py` / `admin_router.py` / `tracking*.py`，业务服务 `services.py`，迁移 `migrations/`（Alembic）。入口 `app.py` 仅为 Uvicorn/测试兼容保留。导入 `app` 即创建 uploads 子目录，`config.py` 缺 `PAYMENT_ENCRYPTION_KEY` 直接抛错——接管期间不启动服务。
- **环境**：本机 Conda `firstenv`（见 `backend/README.md`），容器 Python 3.12-slim 非 root 用户、端口 5600；本地 Compose API 仅绑 127.0.0.1:5600，`AUTO_CREATE_SCHEMA=false`，postgres:16 无宿主机端口。
- **数据模型**：`models.py` 恰好 15 个 `__tablename__`，全在 shop schema；迁移链 01→02→03→04，初始迁移用当前 `Base.metadata.create_all`（非冻结快照），04 对已有订阅表跳过。
- **路由**：静态提取 38 个显式路由定义（routers 20 + admin 12 + tracking 2 + 订阅 3 + /health 1），与报告路由表逐行吻合。
- **认证**：JWT HS256、12 小时、含 `token_version`；重置 token 存 SHA256、30 分钟、单次使用，重置后版本递增使旧 JWT 失效。`forgot-password` 给该邮箱匹配的全部 active 账号各发一条链接（`routers.py:65-76`），响应统一不透露账户存在性。
- **邮箱迁移**：迁移 02 按角色回填默认邮箱并设 NOT NULL（仅普通索引，非唯一约束）；迁移 03 无 WHERE 改写全表邮箱，downgrade 是交换两个默认值而非还原原值。配合"找回邮件发给所有同邮箱账号"的行为，共享邮箱的找回归属问题与报告描述一致，接管后涉及用户邮箱的改动前必须先核对存量数据。
- **订单事务**：下单对购物车项、商品、库存 `with_for_update` 行锁，服务端计价、扣库存、写订单/配送/支付快照、删购物车、写通知与审计后 commit；库存不足或下架回滚 409。地址可省略（旧客户端兼容），前端校验不能当后端约束。支付仅记录微信/支付宝/银行卡意向，无回调、不扣款、不生成运单；银行卡 Luhn 12–19 位、Fernet 加密、HMAC 全局唯一指纹。
- **通知与物流**：飞书通知最多 6 次，启动时 + 每 5 分钟扫描 pending，未配置跳过，失败不撤销订单；SMTP 普通连接 + 可选 STARTTLS，缺配置仅记日志，无持久化重试队列。快递鸟主动查询（缓存 5 分钟/256 条/进程内串行/全局 1 秒间隔）与订阅（先 commit 意图再提交一次，不自动重发；webhook 验签 + 商户 ID + 101/102，1MB/100 单/每单 1000 轨迹，旧批次不覆盖新数据，批次提交成功才确认）均与报告一致。

### 测试定义与已验证事实的区分

- **已验证事实**（本轮静态读源码，基线 `e1259ea`）：上节全部结构性行为。
- **测试定义**（`backend/tests/test_api.py`，14 个测试函数，本轮未执行）：断言弱密码拒绝、邮箱唯一/邮箱登录、重置单次使用及旧登录失效、CORS、物流配置/鉴权/no-store、下单扣库存/不足回滚、富文本图片、地址卡号配送快照、停用恢复、商品生命周期、经营看板。运行载体是 TestClient + 内存 SQLite，无 PostgreSQL 行锁语义；订阅/Webhook、真实邮件投递、通知六次重试无专门测试。
- **未验证**：任何运行时行为（测试结果、服务启动、真实邮件/飞书卡片/快递鸟链路、线上部署版本）。首轮"GET /health 200、/api/products 18 件商品"是此前轮次的运行时证据，本轮未复测；部署专项结论"现有镜像无 revision 标签"沿用 deploy 记录。

## 必要纠正

Mika 报告总体准确，两点表述需精化：

1. **"独立生产 Compose" 指 `deploy/compose.yml`，不是根目录 `docker-compose.production.yml`。** 后者只有 6 行，仅是前端镜像的构建参数覆盖（`NEXT_PUBLIC_API_URL=/api`），不含 api/db 服务，也没有关闭建表/播种的设置。关闭 `AUTO_CREATE_SCHEMA` 与 `SEED_DEMO_DATA` 的生产定义在 `deploy/compose.yml:18-19`。读配置时勿以根目录文件名望文生义。
2. **运单号长度两条路径不同**：主动查询 6–40 位（`shop_api/tracking.py:79`），订阅登记 6–30 位（`shop_api/tracking_subscriptions.py:39`）。报告只在主动物流一节写了 6–40，订阅一节未提，同一单号在两条路径可能一个通过一个被拒。

另补一处澄清（非报告错误）：`email` 在数据库层从未有唯一约束——迁移 02 建的是普通索引 `ix_shop_users_email`，ORM 亦未声明 `unique=True`；唯一性只由注册接口的应用层检查保证，并发注册可产生重复邮箱。

## 后端任务拆分候选

以下为已识别的候选积压项，均**未获得开发授权**；任何一项动工都须来自成员的明确任务，届时再立 issue 定边界。

| 候选 | 内容 | 涉及文件（预估） | 优先级理由 |
| --- | --- | --- | --- |
| 邮箱唯一约束与存量去重 | 数据库层 unique + 迁移前先盘点共享邮箱（迁移 03 遗留），定改写策略 | `migrations/versions/`、`models.py`、`routers.py` | 找回/登录按邮箱匹配多账号，数据问题优先 |
| 评论图片生命周期清理 | 未绑定/未发布图片与失败残留文件的回收 | `services.py`、`routers.py` | 上传目录只增不减 |
| 密码重置邮件持久化重试 | 现为后台任务即发即弃，SMTP 抖动即丢 | `password_reset_email.py`、`routers.py` | 影响找回成功率 |
| 订阅物流与 Webhook 测试 | 现有 14 测试零覆盖：登记幂等、验签、批次合并、旧批次丢弃 | `tests/test_api.py` | 回归风险最高的空白 |
| 通知跨进程幂等 | 多进程/多实例部署时飞书卡片可能重复投递 | `notifications.py` | 单实例部署下暂不紧迫 |
| 订单→运单衔接 | 现为手动 `/api/tracking/status` 登记；是否自动生成属产品决策 | 需先与成员确认需求 | 非缺陷，先讨论 |

## 与 Mika 的协作方式

- **默认分工**：后端开发任务由 claude code 负责；当任务积压或预计无法按期完成时，在本 issue（或父 issue）说明可拆出的后端工作，交 Mika 协调承接。
- **文件边界**（避免并发覆盖）：拆给 Mika 的工作优先选与我在改的文件不相交的单元——例如 `tests/`（Mika 补测试）与我改 `shop_api/` 业务模块、`docs/` 认知文档与我改代码、独立新模块与存量路由。同一文件同一时间窗口只归一人；边界在被拆分任务的 issue 描述里写明。
- **约束沿用**：Mika 承接后端工作时同样遵守——不导入应用/不启动服务、不读真实 `.env`/密钥/业务数据、不发送外部通知；运行验证用 TestClient + 内存 SQLite 或明确授权的本地容器。
- **交接载体**：一切协调走 issue 评论；交接认知写 `docs/understanding/`，开发改动按具体任务授权。

## 后续

后续业务修改须来自明确任务。本接管不产生代码变更、不提交、不部署；本文件与最终评论即本轮全部交付。
