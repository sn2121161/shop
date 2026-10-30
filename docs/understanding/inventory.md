# 项目文件盘点

日期：2026-10-30。覆盖当前 Git 跟踪文件，不含依赖、构建缓存、真实环境文件、运行数据或平台元数据。

表中的「专项负责人」表示后续认知归属，不表示负责人已经完成审阅。二进制图片只登记用途，锁文件用于核对依赖，不将第三方依赖逐包审计。

| 文件 | 类型 / 用途 | 专项负责人 |
| --- | --- | --- |
| `.github/workflows/deploy.yml` | 文本 / 配置 / 源码，89 行 | opencode |
| `.gitignore` | 文本 / 配置 / 源码，57 行 | Mika |
| `LICENSE` | 文本 / 配置 / 源码，21 行 | Mika |
| `README.md` | 已有说明 / 需求 / 设计记录 | Mika |
| `backend/.dockerignore` | 文本 / 配置 / 源码，6 行 | claude code |
| `backend/.env.example` | 无真实凭证的配置模板 | claude code |
| `backend/.gitignore` | 文本 / 配置 / 源码，4 行 | claude code |
| `backend/CONTEXT.md` | 已有说明 / 需求 / 设计记录 | claude code |
| `backend/Dockerfile` | 文本 / 配置 / 源码，13 行 | claude code |
| `backend/README.md` | 已有说明 / 需求 / 设计记录 | claude code |
| `backend/alembic.ini` | 文本 / 配置 / 源码，37 行 | claude code |
| `backend/app.py` | 文本 / 配置 / 源码，9 行 | claude code |
| `backend/migrations/env.py` | 数据库迁移 | claude code |
| `backend/migrations/script.py.mako` | 数据库迁移 | claude code |
| `backend/migrations/versions/20261009_01_initial_shop_schema.py` | 数据库迁移 | claude code |
| `backend/migrations/versions/20261016_02_user_email_password_resets.py` | 数据库迁移 | claude code |
| `backend/migrations/versions/20261017_03_set_account_email_defaults.py` | 数据库迁移 | claude code |
| `backend/migrations/versions/20261027_04_tracking_subscriptions.py` | 数据库迁移 | claude code |
| `backend/pytest.ini` | 文本 / 配置 / 源码，2 行 | claude code |
| `backend/requirements.txt` | 文本 / 配置 / 源码，14 行 | claude code |
| `backend/shop_api/__init__.py` | 文本 / 配置 / 源码，1 行 | claude code |
| `backend/shop_api/admin_router.py` | 文本 / 配置 / 源码，215 行 | claude code |
| `backend/shop_api/config.py` | 文本 / 配置 / 源码，40 行 | claude code |
| `backend/shop_api/database.py` | 文本 / 配置 / 源码，60 行 | claude code |
| `backend/shop_api/main.py` | 文本 / 配置 / 源码，86 行 | claude code |
| `backend/shop_api/models.py` | 文本 / 配置 / 源码，108 行 | claude code |
| `backend/shop_api/notifications.py` | 文本 / 配置 / 源码，116 行 | claude code |
| `backend/shop_api/password_reset_email.py` | 文本 / 配置 / 源码，27 行 | claude code |
| `backend/shop_api/routers.py` | 文本 / 配置 / 源码，244 行 | claude code |
| `backend/shop_api/schemas.py` | 文本 / 配置 / 源码，80 行 | claude code |
| `backend/shop_api/security.py` | 文本 / 配置 / 源码，63 行 | claude code |
| `backend/shop_api/services.py` | 文本 / 配置 / 源码，63 行 | claude code |
| `backend/shop_api/tracking.py` | 文本 / 配置 / 源码，158 行 | claude code |
| `backend/shop_api/tracking_subscriptions.py` | 文本 / 配置 / 源码，204 行 | claude code |
| `backend/tests/test_api.py` | 测试定义（本轮未执行） | claude code |
| `deploy/Dockerfile.api` | 文本 / 配置 / 源码，15 行 | opencode |
| `deploy/Dockerfile.frontend` | 文本 / 配置 / 源码，24 行 | opencode |
| `deploy/README.md` | 已有说明 / 需求 / 设计记录 | opencode |
| `deploy/build-and-test.sh` | 文本 / 配置 / 源码，58 行 | opencode |
| `deploy/build-on-server.sh` | 文本 / 配置 / 源码，68 行 | opencode |
| `deploy/compose.yml` | 文本 / 配置 / 源码，44 行 | opencode |
| `deploy/deploy.sh` | 文本 / 配置 / 源码，109 行 | opencode |
| `deploy/server.env.example` | 无真实凭证的配置模板 | opencode |
| `deploy/unpack-source.py` | 文本 / 配置 / 源码，25 行 | opencode |
| `docker-compose.production.yml` | 文本 / 配置 / 源码，6 行 | opencode |
| `docker-compose.yml` | 文本 / 配置 / 源码，52 行 | opencode |
| `docs/backend-ppt-outline.md` | 已有说明 / 需求 / 设计记录 | Mika |
| `docs/free-shipping-options.md` | 已有说明 / 需求 / 设计记录 | Mika |
| `docs/heroin-i-image-prompt.md` | 已有说明 / 需求 / 设计记录 | Mika |
| `docs/molecular-necklace-image-prompts-batch-2.md` | 已有说明 / 需求 / 设计记录 | Mika |
| `docs/molecular-necklace-image-prompts.md` | 已有说明 / 需求 / 设计记录 | Mika |
| `docs/tracking-webhook.md` | 已有说明 / 需求 / 设计记录 | Mika |
| `frontend/.dockerignore` | 文本 / 配置 / 源码，9 行 | Pi |
| `frontend/.env.example` | 无真实凭证的配置模板 | Pi |
| `frontend/.gitignore` | 文本 / 配置 / 源码，41 行 | Pi |
| `frontend/.openai/hosting.json` | 文本 / 配置 / 源码，4 行 | Pi |
| `frontend/Dockerfile` | 文本 / 配置 / 源码，15 行 | Pi |
| `frontend/app/_sites-preview/SkeletonPreview.tsx` | 文本 / 配置 / 源码，145 行 | Pi |
| `frontend/app/_sites-preview/preview.css` | 文本 / 配置 / 源码，326 行 | Pi |
| `frontend/app/admin/DashboardPanel.tsx` | 文本 / 配置 / 源码，42 行 | Pi |
| `frontend/app/admin/page.tsx` | 文本 / 配置 / 源码，49 行 | Pi |
| `frontend/app/cart/page.tsx` | 文本 / 配置 / 源码，44 行 | Pi |
| `frontend/app/components/MoleculeCard.tsx` | 文本 / 配置 / 源码，46 行 | Pi |
| `frontend/app/components/PickupMap.tsx` | 文本 / 配置 / 源码，129 行 | Pi |
| `frontend/app/components/ProductComments.tsx` | 文本 / 配置 / 源码，72 行 | Pi |
| `frontend/app/data/molecules.json` | 文本 / 配置 / 源码，149 行 | Pi |
| `frontend/app/forgot-password/page.tsx` | 文本 / 配置 / 源码，27 行 | Pi |
| `frontend/app/globals.css` | 文本 / 配置 / 源码，49 行 | Pi |
| `frontend/app/layout.tsx` | 文本 / 配置 / 源码，4 行 | Pi |
| `frontend/app/login/page.tsx` | 文本 / 配置 / 源码，32 行 | Pi |
| `frontend/app/orders/[id]/page.tsx` | 文本 / 配置 / 源码，38 行 | Pi |
| `frontend/app/page.tsx` | 文本 / 配置 / 源码，67 行 | Pi |
| `frontend/app/products/[id]/page.tsx` | 文本 / 配置 / 源码，48 行 | Pi |
| `frontend/app/register/page.tsx` | 文本 / 配置 / 源码，39 行 | Pi |
| `frontend/app/reset-password/page.tsx` | 文本 / 配置 / 源码，34 行 | Pi |
| `frontend/app/shop.tsx` | 文本 / 配置 / 源码，98 行 | Pi |
| `frontend/app/tracking/page.tsx` | 文本 / 配置 / 源码，85 行 | Pi |
| `frontend/db/index.ts` | 文本 / 配置 / 源码，13 行 | Pi |
| `frontend/db/schema.ts` | 文本 / 配置 / 源码，4 行 | Pi |
| `frontend/drizzle.config.ts` | 文本 / 配置 / 源码，7 行 | Pi |
| `frontend/drizzle/meta/_journal.json` | 文本 / 配置 / 源码，5 行 | Pi |
| `frontend/eslint.config.mjs` | 文本 / 配置 / 源码，41 行 | Pi |
| `frontend/examples/d1/app/api/notes/route.ts` | 文本 / 配置 / 源码，58 行 | Pi |
| `frontend/examples/d1/db/schema.ts` | 文本 / 配置 / 源码，9 行 | Pi |
| `frontend/next-env.d.ts` | 文本 / 配置 / 源码，5 行 | Pi |
| `frontend/next.config.ts` | 文本 / 配置 / 源码，18 行 | Pi |
| `frontend/package.json` | 文本 / 配置 / 源码，58 行 | Pi |
| `frontend/pnpm-lock.yaml` | 依赖锁文件 | Pi |
| `frontend/pnpm-workspace.yaml` | 文本 / 配置 / 源码，4 行 | Pi |
| `frontend/postcss.config.mjs` | 文本 / 配置 / 源码，7 行 | Pi |
| `frontend/public/favicon.svg` | 文本 / 配置 / 源码，6 行 | Pi |
| `frontend/public/file.svg` | 文本 / 配置 / 源码，1 行 | Pi |
| `frontend/public/images/adrenaline-necklace.png` | 静态图片素材 / 分子结构或商品图片 | Pi |
| `frontend/public/images/bendazol-necklace.png` | 静态图片素材 / 分子结构或商品图片 | Pi |
| `frontend/public/images/benzene-necklace.png` | 静态图片素材 / 分子结构或商品图片 | Pi |
| `frontend/public/images/caffeine-necklace.png` | 静态图片素材 / 分子结构或商品图片 | Pi |
| `frontend/public/images/cocaine-necklace.png` | 静态图片素材 / 分子结构或商品图片 | Pi |
| `frontend/public/images/design.jpg` | 静态图片素材 / 分子结构或商品图片 | Pi |
| `frontend/public/images/draft.jpg` | 静态图片素材 / 分子结构或商品图片 | Pi |
| `frontend/public/images/ethanol-necklace.png` | 静态图片素材 / 分子结构或商品图片 | Pi |
| `frontend/public/images/heroin-i-necklace.png` | 静态图片素材 / 分子结构或商品图片 | Pi |
| `frontend/public/images/heroin-ii-necklace.png` | 静态图片素材 / 分子结构或商品图片 | Pi |
| `frontend/public/images/lsd-necklace.png` | 静态图片素材 / 分子结构或商品图片 | Pi |
| `frontend/public/images/menthol-necklace.png` | 静态图片素材 / 分子结构或商品图片 | Pi |
| `frontend/public/images/molecules/10624.png` | 静态图片素材 / 分子结构或商品图片 | Pi |
| `frontend/public/images/molecules/12132.png` | 静态图片素材 / 分子结构或商品图片 | Pi |
| `frontend/public/images/molecules/16666.png` | 静态图片素材 / 分子结构或商品图片 | Pi |
| `frontend/public/images/molecules/241.png` | 静态图片素材 / 分子结构或商品图片 | Pi |
| `frontend/public/images/molecules/2519.png` | 静态图片素材 / 分子结构或商品图片 | Pi |
| `frontend/public/images/molecules/446220.png` | 静态图片素材 / 分子结构或商品图片 | Pi |
| `frontend/public/images/molecules/4737.png` | 静态图片素材 / 分子结构或商品图片 | Pi |
| `frontend/public/images/molecules/5202.png` | 静态图片素材 / 分子结构或商品图片 | Pi |
| `frontend/public/images/molecules/5288826.png` | 静态图片素材 / 分子结构或商品图片 | Pi |
| `frontend/public/images/molecules/5761.png` | 静态图片素材 / 分子结构或商品图片 | Pi |
| `frontend/public/images/molecules/5816.png` | 静态图片素材 / 分子结构或商品图片 | Pi |
| `frontend/public/images/molecules/702.png` | 静态图片素材 / 分子结构或商品图片 | Pi |
| `frontend/public/images/molecules/89594.png` | 静态图片素材 / 分子结构或商品图片 | Pi |
| `frontend/public/images/morphine-necklace.png` | 静态图片素材 / 分子结构或商品图片 | Pi |
| `frontend/public/images/nicotine-necklace.png` | 静态图片素材 / 分子结构或商品图片 | Pi |
| `frontend/public/images/pentobarbital-necklace.png` | 静态图片素材 / 分子结构或商品图片 | Pi |
| `frontend/public/images/product.jpg` | 静态图片素材 / 分子结构或商品图片 | Pi |
| `frontend/public/images/psilocybin-necklace.png` | 静态图片素材 / 分子结构或商品图片 | Pi |
| `frontend/public/images/psychedelic-necklace.png` | 静态图片素材 / 分子结构或商品图片 | Pi |
| `frontend/public/images/serotonin-necklace.png` | 静态图片素材 / 分子结构或商品图片 | Pi |
| `frontend/public/images/serotonin-reference.jpg` | 静态图片素材 / 分子结构或商品图片 | Pi |
| `frontend/public/images/thc-necklace.png` | 静态图片素材 / 分子结构或商品图片 | Pi |
| `frontend/public/window.svg` | 文本 / 配置 / 源码，1 行 | Pi |
| `frontend/scripts/sync-molecules.mjs` | 文本 / 配置 / 源码，60 行 | Pi |
| `frontend/tsconfig.json` | 文本 / 配置 / 源码，29 行 | Pi |
| `frontend/types/area-data.d.ts` | 文本 / 配置 / 源码，9 行 | Pi |
| `frontend/vite.config.ts` | 文本 / 配置 / 源码，6 行 | Pi |
| `prompt.md` | 已有说明 / 需求 / 设计记录 | Mika |
| `tests/deployment/test_deploy.py` | 测试定义（本轮未执行） | opencode |
| `tests/deployment/test_unpack_source.py` | 测试定义（本轮未执行） | opencode |

共 134 个 Git 跟踪文件。

## 非跟踪目录的处理

- `AGENTS.md` 和 `.multica/` 是本轮开始时已有的非跟踪运行材料，保留原样。
- 本地 `.env` 仅检查存在性，不读取内容；uploads 不读取业务内容。
- 新增认知文件全部位于 `docs/understanding/`，含分工说明、总览、专项报告（待负责人交付）、后续复核指令及文件哈希基线。
- 非 docs 跟踪文件内容与本轮起始哈希比对；比对不涵盖 Git 元数据和被忽略的运行文件。
