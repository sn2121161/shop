# 后端认知：框架、环境与现有服务

记录人：Mika（接替 Pi）。日期：2026-10-30，任务 TTXL-2，父任务 TTXL-1。
源码基线：dev，`e1259eaf729f26eb51b81144d7d3f096c0789821`。

Pi 的模型服务在开始执行时返回凭证无效的 401，任务最终失败，未生成报告且无自动重试。本报告由 Mika 补齐，不能作为 Pi 已完成学习的证明；没有更改 Pi 的模型、凭证或权限。

只读检查范围包括 backend 的 31 个跟踪文件及相关 Compose。没有导入应用或执行测试/迁移/启动服务：应用导入会创建上传目录，lifespan 可能建表、种子数据及重试外部通知。实际服务证据引用首轮已有容器的只读 GET 检查，和源码事实分别说明。真实 `.env`、业务库、上传文件、密钥未读取。

## 架构与本地环境

当前是 FastAPI，不是原始 prompt.md 所设想的 Flask。`requirements.txt` 固定 FastAPI 0.128.0、Uvicorn 0.40.0、SQLAlchemy 2.0.45、psycopg2-binary 2.9.11、PyJWT 2.11.0、Werkzeug 3.1.4、Alembic 1.15.1、pytest 9.0.2 等。密码哈希用 Werkzeug，富文本白名单用 bleach/tinycss2，银行卡用 cryptography.Fernet，外部 HTTP 用 httpx。

| 模块 | 职责 |
| --- | --- |
| `app.py` / `shop_api/main.py` | 兼容入口、应用工厂、lifespan、路由组装、静态上传目录、CORS、HTTPException JSON 和请求状态日志 |
| `config.py` | dotenv 和环境变量，初始化 Fernet |
| `database.py` | SQLAlchemy engine/session；SQLite 测试 schema 映射及兼容补列 |
| `models.py` / `schemas.py` | ORM 表关系与持久化序列化；Pydantic 输入校验 |
| `security.py` | JWT、活跃用户/管理员依赖、银行卡 Luhn/HMAC |
| `routers.py` / `admin_router.py` | 顾客和管理业务接口 |
| `services.py` | 图片保存、评论清洗、购物车序列化及演示种子 |
| `password_reset_email.py` / `notifications.py` | SMTP 密码邮件与飞书订单通知 |
| `tracking.py` / `tracking_subscriptions.py` | 快递鸟主动查询、订阅意图和推送入库 |
| `migrations/` | Alembic 版本链；生产正式表结构更新 |

表中未带目录的 Python 文件均在 `backend/shop_api/`。

本机 README 要求进入 backend，以 Conda firstenv 执行 Uvicorn/pytest。首轮确认 firstenv 存在、当前 PATH Python 为 3.12.1，但未验证 firstenv 内每项依赖。Dockerfile 使用 Python 3.12-slim，以非 root shop 用户启动 Uvicorn 5600；本地 Compose 中 API 仅映射 127.0.0.1:5600，数据库由 postgres:16 容器提供且无宿主机映射。

直接本机运行的默认连接是数据库 nzw、schema shop；Compose 读取 backend/.env，不能假定沿用这个默认值。PAYMENT_ENCRYPTION_KEY 必须是有效 Fernet key，缺失会在导入时报错；JWT_SECRET 源码有开发默认值。配置模板未给出 DATABASE_URL/JWT_SECRET/PostgreSQL 用户密码的完整生产配置，不可将模板直接视为可用部署。SMTP、飞书及物流参数按功能另行配置，前端公网 URL 用于重置链接。

AUTO_CREATE_SCHEMA、SEED_DEMO_DATA 的源码默认均为 true。独立生产 Compose 显式关闭二者，使用 Alembic。根本地 Compose 仅显式关闭自动建表，是否播种取决于环境；不要以学习为由直接启动指向未知数据库的应用。

## 数据模型与迁移

`models.py` 定义 15 个表，均在 shop schema：

| 表 | 数据与关系 |
| --- | --- |
| users | 唯一用户名、邮箱、密码哈希、角色/状态、token_version |
| password_reset_tokens | 用户外键、唯一 token 哈希、过期/使用时间 |
| default_addresses | 每用户唯一默认地址，与订单历史地址分离 |
| payment_methods | 用户、加密卡号、全局唯一卡指纹、末四位 |
| products / inventory | 唯一商品名、价格/故事/上下架；库存按商品主键且数量 >=0 |
| cart_items | 用户 + 商品唯一，关联商品及数量 |
| orders / order_items | 用户订单及名称/单价/数量快照 |
| order_fulfillments | 每订单唯一，配送费/服务、地址/自提、模拟支付快照 |
| order_notifications | 每订单唯一，飞书投递状态、次数、错误、时间 |
| audit_logs | 操作者、动作、目标、前后值及时间 |
| comments / comment_images | 商品留言、作者名快照；图片归上传用户且可绑定评论 |
| tracking_subscriptions | 公司 + 运单唯一，订阅状态、轨迹 JSON、推送/同步时间 |

迁移链为 20261009_01 → 20261016_02 → 20261017_03 → 20261027_04。初始迁移使用当前 Base.metadata.create_all，因而不是冻结的历史模型快照；04 对已存在的订阅表跳过创建。02 为缺邮箱用户按角色填相同默认地址；03 无 WHERE 条件改写全表邮箱，downgrade 也不是恢复原值。生产是否执行过不能用本地文件判断；认知任务没有执行这些迁移。

`migrations/env.py` 从环境读取 DATABASE_URL，include_schemas=true；`database.py` 的兼容补列与 Alembic 是不同机制，不可拿自动建表替代正式迁移流程。

## 核心业务和权限

注册要求至少三位字母数字下划线账号、有效邮箱、至少九位且包含大小写/数字/特殊字符的密码，两次相同；邮箱归一化后检查唯一。邮箱在 ORM 层未声明唯一约束，注册检查不是数据库并发唯一性保证。

登录接受账号或邮箱；按邮箱登录会在匹配的账户中核对密码。JWT 为 HS256，12 小时，含用户 ID 和 token_version；每次鉴权查用户并验证版本。active_user 拒绝停用用户，current_admin 还检查 admin 角色。重置 token 存 SHA256 哈希，有效期 30 分钟、单次使用，重置密码递增版本使旧 JWT 失效。找回邮箱响应不透露账户是否存在，但给该邮箱匹配的全部 active 账号逐个发送链接，因此全表默认邮箱迁移会改变多个账户的找回归属。

商品公开接口仅列上架商品；购物车按当前用户隔离，加购不预占库存。下单对购物车、商品及库存加行锁，计算服务端价格和配送费、扣库存、保存订单/配送快照、删除选中购物车项并写审计与通知记录，再 commit。库存不足或已下架回滚返回冲突。地址在后端仍可省略以兼容旧客户端，前端表单较严格；不能将前端校验当成后端强制约束。

配送含自提、顺丰次日达（5 元）及四种免费快递，还兼容 standard 别名。支付只记录微信/支付宝/银行卡意向，不接收支付回调、不扣款、不生成运单；卡号经过 12–19 位 Luhn 校验、Fernet 加密及 HMAC 指纹，响应只给末四位。密钥变更会影响旧数据解密与指纹匹配，不能随意重置。

评论先清洗 HTML/CSS 白名单，检查所有图片归当前用户、尚未绑定，且正文引用 URL 集合与声明图片一致。图片支持 JPG/PNG/WebP/GIF、大小不超过 5MB，保存 UUID 文件名；源码依赖上传声明的 MIME 类型，没有对图片内容解码验证。上传写文件先于数据库提交，失败/未发布图片的清理未在当前服务中实现。

管理员可查用户、停用/恢复非管理员；上传/新建/补货/上下架/调价商品；查审计和经营看板。变更记录前后值，订单/商品统计库存含义为当前库存。看板按上海时区汇总，趋势/排行的时间范围与订单明细的额外筛选分开；销售额来源是模拟订单，不能当实际收款。

## 外部集成与可靠性

- SMTP：普通 SMTP + 可选 STARTTLS，可登录授权；没有 SMTP_SSL 465 分支。缺配置会记录未发送，不保证实际投递；邮件使用后台任务，没有持久化邮件重试队列。
- 飞书：只做出站订单卡片，包含账号、明细、电话和地址；订单先成功提交再异步发信，失败不撤销订单。启动时及每五分钟扫描 pending，最多六次；未配置时跳过，SQLite 测试不启动通知循环。该机制不保证跨进程并发投递严格不重复。
- 主动物流：快递鸟 1002/8002，支持圆通/申通/极兔/百世。运单清理为空格删除/大写，6–40 位；按用户+公司+单号缓存五分钟，上限 256 条，进程锁串行请求且全局间隔一秒。缓存/限流不跨进程共享。
- 订阅物流：1008/8008，有效回调配置才启用；先 commit 公司+单号唯一意图，再向服务商提交一次。active/rejected/uncertain/pending 不自动重发，避免受理后超时重复提交。`/query` 在订阅启用时也走该逻辑，`/status` 是显式登记入口。
- Webhook：无需用户 JWT，依赖原始 RequestData 签名、商户 ID 和通知类型 101/102 校验；最多 1MB/100 单、每单轨迹最多 1000 项。未知单号确认但不存，已登记单号行锁合并轨迹，旧批次不覆盖新数据，批次提交成功才确认。知晓单号的登录用户可查同一订阅，未绑定用户或订单归属；它沿用凭单号查询模型。

以上只证明代码存在。没有发邮件/飞书卡片、查询真实运单或模拟回调；权限、额度、服务商可用性和公网链路未验证。

## 测试与实际运行证据

`backend/tests/test_api.py` 有 14 个测试函数，覆盖弱密码、邮箱唯一/邮箱登录、重置单次使用及旧登录失效、CORS、物流配置/鉴权/no-store、下单扣库存/不足回滚、富文本图片、地址卡号配送快照、停用恢复、商品生命周期及经营看板。使用 TestClient + 内存 SQLite；SQLite 将 shop schema 映射为空，没有 PostgreSQL 行锁语义。未发现专门的订阅/Webhook、真实邮件投递或通知六次重试测试，不能由现有用例推断这些已验收。

首轮 Mika 只读 GET 已确认现有本地 API /health 为 200、status=ok，前端代理 /api/products 为 200 且返回 18 件商品；部署专项补充现有镜像无 revision 标签，故不能证明当前源码已部署。此轮未重新运行测试或应用。

## 全部业务路由索引

下表从当前源码 AST 静态提取，不导入应用。鉴权规则以各函数的 Depends 和上述权限说明为准；FastAPI 自动文档与 /uploads 静态挂载另计。

| 方法 | 路径 | 源码 |
| --- | --- | --- |
| POST | `/api/auth/register` | `routers.py:39` |
| POST | `/api/auth/login` | `routers.py:51` |
| POST | `/api/auth/forgot-password` | `routers.py:63` |
| POST | `/api/auth/reset-password` | `routers.py:82` |
| GET | `/api/auth/me` | `routers.py:103` |
| GET | `/api/products` | `routers.py:110` |
| GET | `/api/products/{product_id}` | `routers.py:115` |
| GET | `/api/products/{product_id}/comments` | `routers.py:123` |
| POST | `/api/comment-images` | `routers.py:129` |
| POST | `/api/products/{product_id}/comments` | `routers.py:134` |
| GET | `/api/account/address` | `routers.py:149` |
| PUT | `/api/account/address` | `routers.py:155` |
| GET | `/api/payment-methods` | `routers.py:164` |
| POST | `/api/payment-methods` | `routers.py:169` |
| GET | `/api/cart` | `routers.py:179` |
| POST | `/api/cart` | `routers.py:183` |
| PATCH | `/api/cart/{item_id}` | `routers.py:193` |
| DELETE | `/api/cart/{item_id}` | `routers.py:200` |
| POST | `/api/orders` | `routers.py:207` |
| GET | `/api/orders/{order_id}` | `routers.py:241` |
| GET | `/api/admin/dashboard` | `admin_router.py:52` |
| GET | `/api/admin/users` | `admin_router.py:114` |
| POST | `/api/admin/users/{user_id}/disable` | `admin_router.py:129` |
| POST | `/api/admin/users/{user_id}/restore` | `admin_router.py:139` |
| GET | `/api/admin/products` | `admin_router.py:149` |
| POST | `/api/admin/products/images` | `admin_router.py:160` |
| POST | `/api/admin/products` | `admin_router.py:165` |
| POST | `/api/admin/products/{product_id}/restock` | `admin_router.py:174` |
| POST | `/api/admin/products/{product_id}/unlist` | `admin_router.py:183` |
| POST | `/api/admin/products/{product_id}/relist` | `admin_router.py:191` |
| POST | `/api/admin/products/{product_id}/price` | `admin_router.py:200` |
| GET | `/api/admin/audit-logs` | `admin_router.py:212` |
| GET | `/api/tracking/options` | `tracking.py:148` |
| POST | `/api/tracking/query` | `tracking.py:154` |
| GET | `/api/tracking/subscription-options` | `tracking_subscriptions.py:117` |
| POST | `/api/tracking/status` | `tracking_subscriptions.py:122` |
| POST | `/api/tracking/webhook` | `tracking_subscriptions.py:129` |
| GET | `/health` | `main.py:83` |

共 38 个显式业务/健康路由定义。
