# 前端交接认知：Pi 的复核、多模态观察与待确认项

记录人：Pi。日期：2026-10-30（Asia/Shanghai）。任务：TTXL-3，父任务 TTXL-1。
基线：本地 `dev`，提交 `e1259eaf729f26eb51b81144d7d3f096c0789821`。

本轮是交接认知，不是开发修复。我（Pi）按新分工接管前端，复核了 opencode 的原报告 `frontend.md`（保留原作者与历史结论），核对了核心源码，并用多模态能力查看了静态图片素材。本文件是我唯一写入位置；没有修改源码、配置、素材或已有报告，没有安装依赖、构建、运行检查、提交或推送，没有操作真实账户或下单，没有读取真实环境文件内容。

本环境的工具边界：没有浏览器工具，无法截图页面；图片观察是直接读取本地素材文件的真实视觉证据；对现有 `localhost:3000`（本地 Compose 容器已在运行，本轮未启动/停止任何服务）只做了只读 GET 探测来验证 HTML 结构，这属于"页面源码/响应推断"，不是浏览器视觉验收。两类证据在下文分开标注。

## 1. 对原报告的复核结论

原报告（opencode，`docs/understanding/frontend.md`）的主要结论经我逐条抽查源码后**全部成立**，无异议：

- 栈为 React 19.2.6 + Vinext 1.0.0-beta.2 + Vite 8.0.13，`package.json` 依赖中确实没有 `next`；`next.config.ts` 的两条 rewrite 指向 `http://api:5600`，与原文一致。
- 首页 `app/page.tsx:63` 硬编码 `THE COLLECTION / 17 PIECES`；`app/page.tsx:14` 的 `useSyncExternalStore` 服务端快照固定为 `false`。
- `app/shop.tsx:9` 按 `/admin` 路径前缀切换会话 scope；`:13` 的 `loginRedirectPending` 防并发重复跳转；`:26-44` 的 `productImages` 静态映射覆盖逻辑与原文描述一致。
- `app/globals.css` 的配色变量（`--cream #f6f2ea`、`--paper #fffdf9`、`--moss #265842`、`--gold #c49751`、`--ink #17201c`）、Georgia/Songti 衬线标题、`max-width:820px` 隐藏 `.topbar nav` 与 `.header-actions>a:not(.cart-link)` 等断点规则均逐字确认。结账区确实硬编码 `#1677ff`（AntD 默认蓝）且大量使用 `!important`。
- 本机 Node v24.13.0、pnpm 11.21.0，满足 `engines.node >=22.13.0` 与 `packageManager pnpm@11.21.0`（本轮实测命令输出）。

## 2. 本轮新增的实证（只读 GET 探测）

以下是对已运行的本地服务做只读 GET 的结果，属于响应级证据，非浏览器视觉：

- `GET http://localhost:3000/` 返回 200，HTML 约 10 KB。**body 实测为 `<div class="site-shell" aria-busy="true"></div>` 加一串 RSC/Vite 脚本标签**——首页 SSR 空壳从"源码推断"升级为"响应实证"：首屏 HTML 不含任何商品、文案或导航，全部依赖客户端 JS 渲染。
- `GET http://localhost:3000/api/products` 返回 200，共 **18 件**商品。第 18 件为 **「破碎的心」**（id 18），图片字段是 `/uploads/products/804fdae4c20e4b7bbe412b77d01bfb2f.png`（后台上传图）。其余 17 件的 `image` 字段全部是 `/images/product.jpg`。
- 由此可闭环 17/18 差异的展示链路：
  1. 「破碎的心」不在 `productImages` 静态表中，会走 `productAssetUrl` 显示后台上传图，是 18 件中唯一展示真实上传图的商品；
  2. 它也不在 `molecules.json`，详情页会显示通用"结构待确认"分子卡；
  3. 首页标题仍写 17 PIECES，网格实际渲染 18 件——文案漂移在运行时可复现。
- 另一层细节：数据库里 17 件种子商品的 `image` 都是占位值 `/images/product.jpg`，前台之所以显示各自的珠宝图，**完全依赖 `productImages` 按中文名的精确字符串匹配**。这意味着后台若改动商品名（哪怕加一个空格），静态图与分子资料会同时静默失效并回退到占位图/待确认卡。这是一个此前报告未明确点破的脆弱点。

## 3. 多模态图片观察（真实视觉证据）

以下是对 `frontend/public/images/` 素材的直接视觉读取，共查看 6 张：

| 文件 | 视觉内容 |
| --- | --- |
| `design.jpg`（首页英雄区） | 白底手绘铅笔/彩铅设计草图，四款项链设计：**去甲肾上腺素 C₈H₁₁NO₃**（红钻心形主石）、**血清素 C₁₀H₁₂N₂O**（靛蓝珐琅六边形、海蓝宝心形主石、黄钻点缀）、**苯乙胺 C₈H₁₁N「怦然心动」**（粉钻心形）、**多巴胺 C₈H₁₁NO₂**（粉钻心形、太阳花黄钻扣头）。手写标注「珐琅」「海蓝宝」「红钻」「粉钻」「黄钻」。与商品图的最终效果一一对应，是"从手稿到成品"叙事的核心素材。 |
| `draft.jpg`（首页故事区） | 实拍照片：粉色桌垫上 iPad 显示血清素项链的手绘草图（与 design.jpg 中间那款同一设计），背景有键盘与数据线，图库 App 界面可见。传达"手作设计过程"的真实感。 |
| `serotonin-necklace.png` / `benzene-necklace.png` / `lsd-necklace.png` / `heroin-i-necklace.png`（商品图） | 风格高度统一的珠宝微距渲染：浅蓝色纯色背景、抛光黄金链条与轮廓、**午夜蓝珐琅**骨架、**心形海蓝宝切面主石**嵌于中央、浅蓝/浅粉/白色圆形 cabochon 作为分子节点，节点间以金色小球连接。LSD 款结构延展最大，血清素款带吲哚双环。与 `docs/molecular-necklace-image-prompts*.md` 的视觉规范完全吻合。 |
| `molecules/5202.png`（血清素结构图） | PubChem 标准二维骨架式：苯环并吡咯（吲哚）骨架、酚羟基、乙胺侧链，灰底细线化学绘图，300×300。与珠宝图形成"科学—饰品"对照。 |
| `product.jpg`（未被页面引用） | 黑白线稿的分子项链**目录插图**：4×4 网格展示苯、尼古丁、血清素、肾上腺素、咖啡因、可卡因、海洛因、LSD、吗啡、地巴唑、戊巴比妥、薄荷醇、乙醇（吊牌刻字 C₂H₅OH）、THC（画成了耳环）、迷幻剂、裸盖菇素等。它是数据库 17 件种子商品的 `image` 占位值，但前台被静态映射覆盖，访客看不到它；它更像早期的产品全家福参考图。 |

视觉层面的补充判断：

- 商品图的浅蓝背景与 UI 的米白/苔绿/金色体系**不是同一套色板**，但金色链条与 `--gold`、心形主石的暖色点缀与整体手作调性协调，视觉上不冲突；这是"珠宝摄影图 + 档案纸面 UI"的混搭，属于设计语言的一部分而非缺陷。
- 草图（design.jpg/draft.jpg）与成品渲染图叙事连贯，首页"灵感→系列→创作说明"的结构有真实素材支撑。
- 海洛因 I/II 型、THC、迷幻剂四件有成品渲染图但无分子数据，分子卡显示"结构待确认"——视觉上成品先行、科学资料留白，与 `ambiguousNames` 的谨慎文案一致，是合理的现状。

## 4. 接管后要记住的工程要点

1. **命令是 `vinext dev/build/start`，不是 `next`**；`next/link`、`next/image`、`next/navigation` 是 Vinext shim。源码注释声明 Link 存在 RSC 运行时错误，站内跳转大量用原生 `<a>`/`window.location`（整页刷新），改动导航前先在运行环境复现该限制。
2. **pnpm 11.21.0 + Node ≥22.13.0**，锁文件已提交，Docker 用 `--frozen-lockfile`；`pnpm test` 实际只是 `tsc + eslint`，没有单元/E2E 测试。
3. **代理前提**：`/api`、`/uploads` 重写到 Compose 服务名 `api:5600`，宿主机直接 `pnpm dev` 需要 hosts 映射或把 `NEXT_PUBLIC_API_URL` 改成绝对地址（改公开变量必须重新构建）。
4. **会话是双 scope localStorage JWT**（`mystery_customer_*` / `mystery_admin_*`），按路径前缀切换；401/停用由 Axios 拦截器统一跳 `/login?reason=...`；真正权限在后端。
5. **图片链路三级回退**：`productImages` 中文名精确匹配 → 后端 `image` 字段（`/uploads/` 拼 API 源站）→ 无图。改商品名会破坏第一级；首页 17 张约 29 MB PNG 无懒加载全部即载。
6. **UI 体系**：CSS 变量集中在 `globals.css`（超长单行、`.delivery-option` 规则重复、大量 `!important` 覆盖 AntD）；AntD 无主题定制，默认蓝与苔绿并存；GSAP 动效有 `prefers-reduced-motion` 保护；`<=820px` 隐藏登录/注册入口且无汉堡菜单替代。

## 5. 待确认项（留给后续任务，本轮未验证）

- 浏览器视觉验收：hydration 后首页/详情/购物车/后台的真实渲染、GSAP 动效、移动端断点与登录入口缺口——需要浏览器工具或人工确认，本轮环境不具备。
- Vinext Link RSC 运行时错误的实际复现与修复路径（注释声明，未实测）。
- 第 18 件商品「破碎的心」的运营意图：是否补静态图/分子资料、是否把首页数量文案改为动态计算。
- `pnpm check` / `pnpm build` 在当前源码与全新克隆（缺 `.next/types/routes.d.ts`）下是否通过——本轮未运行。
- 高德地图 SDK 加载、自提点坐标、富文本 XSS 依赖后端清洗的边界——未实测。
- 商品图 29 MB 的实际网络传输成本与懒加载/压缩收益——需 Lighthouse 或网络面板实测。

## 6. 边界声明

本轮只写本文件；没有修改源码、配置、素材或 `frontend.md` 等已有报告；没有安装/构建/测试/提交/推送/创建 PR/部署；没有登录、加购、下单或调用任何写接口；没有读取 `.env.local`、后端 `.env` 或上传目录内容。对 `localhost:3000` 的探测均为只读 GET。图片均来自仓库内素材文件，观察结论是视觉描述，不构成版权/授权核查。
