# 分子商城项目认知与接管总览

Mika 汇总，2026-10-30（Asia/Shanghai），任务 TTXL-1。新分工交接及 SSH 巡检均已交付，主任务与三个子任务进入 in_review，等待成员验收，done 留给成员。

## 当前分工与交付

| 职责 | 负责人 | 当前交付（docs/understanding/ 下） |
| --- | --- | --- |
| 主理、协调及后端繁忙时协助 | Mika | overview.md、项目级共享提示词 |
| 前端与多模态图片/UI 认知 | Pi | frontend-pi-handoff.md |
| 后端开发与服务认知 | claude code | backend-claude-handoff.md |
| 部署运维与 SSH 只读巡检 | opencode | server-opencode-check.md |

Pi 已成功完成本轮前端接管；此前模型凭证错误为历史记录，不再作为当前阻碍。旧 frontend.md（opencode）、backend.md（Mika）、operations.md（claude code）保留作者与历史查询时间。当前职责以本表和项目共享上下文为准。

精简共享提示词已写入平台「分子商城项目」说明，后续项目任务自动获得；本地副本为 project-shared-prompt.md。共享内容只保留分工、架构、环境、服务器入口、生产项目/卷名和操作边界；动态检查结果在带时间的报告中查阅。

## 产品、架构与环境

商城「我的神秘小屋」销售分子主题手作项链，包含商品故事/图片、注册登录与找回、评论、购物车、模拟订单、管理后台和经营看板。支付只记录意向，不实际扣款；订单不自动生成快递运单。原始 prompt.md 中 Flask 等构想已被当前实现替代。

- 前端 frontend/：React 19、Vinext/Vite、TypeScript、Ant Design、Zustand、Axios、GSAP，pnpm；app/ 和 next/* 为 Next 风格接口，脚本实际调用 Vinext。米白/苔绿/金色、衬线标题、手作素材与故事。Cloudflare D1/R2 示例未参与商城。
- 后端 backend/：FastAPI、SQLAlchemy、Alembic、JWT、PostgreSQL 的 shop schema；入口 app.py，shop_api 下按配置、数据、校验、安全、路由及服务分层。15 张表、38 个显式路由，另有 SMTP、飞书订单通知、快递鸟查询/订阅回调。
- 本机开发使用 Conda firstenv；Node >=22.13.0，pnpm 11.21.0。首轮发现 Node v24.13.0、PATH Python 3.12.1，确认 firstenv 存在，未验证该环境依赖是否齐全。
- 本地 Colima/Docker Compose：frontend:3000 代理 /api、/uploads 到 api:5600，再访问 PostgreSQL 16；API 只映射宿主机 127.0.0.1:5600，数据库无宿主机端口。宿主机直接启动前端时不能假设 Docker 服务名 api 可解析。
- 配置分别位于 backend/.env、frontend/.env.local，认知中只检查存在性并读取示例，不读取真实配置。应用导入/启动可能创建上传目录、初始化数据或重试外部通知，本任务没有导入或启动应用。

## 新负责人复核结果

Pi 核对了前端架构、会话、代理、样式和图片映射，并直接观察仓库图片素材。对已有本地服务的 GET 显示：首页服务端 HTML 为空壳，依赖客户端加载；商品接口返回 18 件，第 18 件「破碎的心」走上传图，首页文案仍固定为 17 件。已记录静态图片和分子资料按商品名匹配、移动端登录入口隐藏等现状。Pi 没有浏览器工具，图片观察不等于完成页面级视觉与交互验收。

claude code 对后端静态核对无接管阻碍，并确认两点：关闭自动建表/播种的独立生产定义是 deploy/compose.yml，根 docker-compose.production.yml 仅为覆盖文件；主动物流单号校验为 6–40 位，订阅为 6–30 位。14 个 API 测试函数仅确认定义存在，未执行；SQLite 测试不能证明 PostgreSQL 并发锁行为。后端目前无须拆出的积压任务；后续繁忙时 Mika 按明确任务和不交叉的文件边界协助。

## 线上 SSH 巡检结果

以下依据 opencode 于 2026-10-30 15:07–15:09 的只读实测，表示当时状态，不保证之后持续不变。完整证据见 server-opencode-check.md。

| 项目 | 已核实的结果 |
| --- | --- |
| SSH 与目录 | ubuntu@106.55.2.188，私钥 ~/.ssh/tencent.pem 仅用于认证；严格主机校验通过，/srv/shop 存在 |
| 部署版本 | deployed-sha 为 143a32f6290ab326dfd3b053843b38fb04c36f6f，与当时 GitHub main 一致；current 指向该 SHA、run 40680345985 的发布目录 |
| 容器 | app-api-1、app-frontend-1、app-db-1 均运行，重启次数 0；db healthy，api/frontend 无 Docker healthcheck，以 HTTP 检查为证 |
| 镜像/端口 | api/frontend 为 linux/amd64，revision 标签与部署 SHA 一致；API 127.0.0.1:5600，前端 0.0.0.0:3000，数据库无宿主机映射 |
| 项目/持久化 | Compose 项目 app；卷 app_shop_postgres、app_shop_uploads，不能套用本地 shop 项目卷名 |
| HTTP | 服务器本机 /health、API /api/products、前端首页均 200；未从公网客户端验证 |
| 磁盘 | 根分区 67%，可用约 13G；Docker 构建缓存约 7.8GB 可回收，未执行清理 |
| 备份 | 10 个 sql.gz，最近为 10-28 发布前；只核对元数据，未验证可恢复性 |

数据库容器保留旧 /srv/shop/app 的 Compose 标签，而 api/frontend 使用当前发布目录，与发布脚本只替换应用容器的设计一致。服务器上另有历史目录/配置文件名，仅登记，未读取其内容。

发布链路为 main 推送 → GitHub 测试 → SSH 传固定提交源码 → 服务器构建 → 备份 → Alembic 迁移 → 替换应用 → 健康检查。迁移前失败不切换应用，迁移或切换后失败可能已改变数据库/容器，不会自动回滚数据库。操作前读 deploy/README.md，保留生产项目与卷。

## 已知影响与未验证项

- 历史 20261017_03 迁移无 WHERE 改写用户邮箱，downgrade 也非原值恢复；与同邮箱多个账户找回逻辑耦合。生产实际数据影响未查询，未修复。
- 邮箱唯一性仅由注册应用逻辑检查，数据库没有唯一约束；源码现状不等于已验证并发行为。
- 公网/HTTPS/反代、浏览器 hydration 后的视觉和交互、真实 SMTP/飞书/快递鸟投递与额度、数据库实际迁移版本、备份恢复及上传卷备份均未验收。
- 镜像、构建缓存和发布目录的保留清理需要后续明确任务；当前没有实施清理或配置修改。

## 修改范围与证据边界

本任务所有仓库写入均在 docs/understanding/，另有成员授权的平台项目共享上下文更新。128 个非 docs 跟踪文件与初始 baseline-outside-docs.json 的 SHA256 全部一致；文件盘点见 inventory.md（134 个原有跟踪文件，图片仅作登记，Pi 另完成部分素材观察）。

没有修改业务代码、配置、迁移、素材；没有安装、构建、运行测试、提交、推送或创建 PR；没有重启、部署、迁移、改权限或发送外部通知。opencode 的 SSH 仅执行有界只读查询，没有读取真实 .env、私钥内容、业务数据或日志正文。

此次认知和新接管的交付已齐备。后续开发、视觉验收、外部链路验证或运维改动应由对应负责人按具体任务执行。
