分子商城：我的神秘小屋，销售分子主题手作项链。Git 版本控制：https://github.com/sn2121161/shop

- 分工：Pi 前端（多模态审图/UI）；claude code 后端；opencode 部署运维；Mika 主理协调，后端积压或负责人繁忙时主动承接明确范围的修改，协调文件边界。
- 前端 frontend/：React、Vinext/Vite、TypeScript、Ant Design、Zustand、Axios、GSAP、pnpm；Next 风格 app/ 路由。米白/苔绿/金色、衬线标题与手作图片。
- 后端 backend/：FastAPI、SQLAlchemy、Alembic、JWT；本机 Conda firstenv，PostgreSQL 的 shop schema。已有账户、商品、评论、购物车、订单、后台、邮件、飞书通知、快递鸟物流；支付为模拟，订单不自动生成运单。
- 本地 Colima/Docker Compose：frontend:3000 → /api、/uploads → api:5600 → PostgreSQL 16；API 宿主机仅绑定 127.0.0.1。配置分放 backend/.env、frontend/.env.local，凭证不入库/输出。
- 腾讯云目录 /srv/shop，生产 Compose 项目 app，卷 app_shop_postgres / app_shop_uploads（2026-10-30 巡检确认）。opencode 只读巡检：`ssh -o BatchMode=yes -o ConnectTimeout=15 -i ~/.ssh/tencent.pem ubuntu@106.55.2.188`；私钥仅认证，现场状态须实测。
- main 推送触发测试、SSH 传源码、服务器构建、备份/迁移/健康检查；沿用生产卷和服务器配置。操作发布先读 deploy/README.md；旧邮箱迁移会统一改写用户邮箱。
- 领域交接先读 docs/understanding/overview.md，再按其中索引读当前负责人报告；线上实测见 server-opencode-check.md。认知任务仅写 docs，开发修改按任务授权；巡检只读，重启/发布/迁移另按授权。

项目协作与交付规则（成员明确要求，所有参与本项目的智能体共同遵守）：
- 每个大问题由 Mika 统一创建和管理一个问题级共享分支，覆盖该问题所有子任务，最终只交付一个汇总 PR。Mika 派工时写明唯一工作目录、共享分支、目标分支和各自文件边界；子任务直接使用这份目录和分支。缺少这些信息时先只读核查并向 Mika 报告，不自行创建替代工作环境。
- 子智能体负责分配范围内的探索、修改、测试及结果报告；不得自行创建/切换分支、创建 worktree、克隆或复制整套项目，也不得自行提交、推送、创建/合并/关闭 PR。所有 Git 提交、推送、PR 管理及整合验证统一由 Mika 完成。此规则取代子任务默认独立分支或独立 PR 的交付惯例。
- 同一共享分支按文件边界协作，涉及同一文件或交叉改动由 Mika 安排串行处理。保留成员未提交改动与其他任务文件，任何参与者均不得擅自 reset、清理或覆盖。已有未合并 PR 由 Mika 汇总后统一收口，成员只需审查和合并一个 PR。
- 复用现有项目工作目录；.multica 仅存放本地任务元数据和必要临时记录，不再按智能体存放完整项目副本。统一构建与验收由 Mika 完成；部署沿用既有授权与确认边界。
- 成员明确要求不唤醒其他智能体时，Mika 独立处理，不通过提及、指派、子任务或唤醒规则启动其他智能体。
- 工作目录清理：Mika 在任务收口时检查遗留工作树；确认改动已提交并推送或已合并、没有运行中的任务、没有未保存源码后，使用 git worktree remove 清理旧目录及其可再生成的依赖/构建产物。发现未提交源码先保留并处理；保留主工作目录、成员文件及已推送的提交，不以创建 PR 本身代替保存检查。
