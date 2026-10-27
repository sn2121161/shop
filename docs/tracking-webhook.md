# 物流订阅与回调

目标：首次登记快递公司和单号，向快递鸟提交订阅；后续页面请求只读数据库，不轮询快递鸟。

## 本地测试与公网测试的区别

本地可以验证签名、轨迹入库、去重和页面展示，但快递鸟实际推送会到它控制台保存的公网地址。服务器和本地的 Docker 数据库是两套数据：在本地登记单号、却把回调发到服务器，服务器没有那条订阅，就只会确认接收并忽略它。

真实链路请统一使用 [公网商城](http://106.55.2.188:3000/tracking) 登记和查看。控制台回调格式校验已经通过；真实运单的订阅权限、受理和推送仍需分别验收。

## 服务器后端配置

编辑 `/srv/shop/backend/.env`，保留已有数据库、JWT、支付加密、SMTP 等配置，只追加或修改下列项。不要用开发机的整份配置覆盖生产配置。

```dotenv
KDNIAO_EBUSINESS_ID=你的快递鸟用户ID
KDNIAO_API_KEY=你的快递鸟APIKey
KDNIAO_REQUEST_TYPE=8002
KDNIAO_SUBSCRIBE_REQUEST_TYPE=1008
KDNIAO_CALLBACK_URL=http://106.55.2.188:3000/api/tracking/webhook
```

- 1008 是本次使用的标准物流跟踪订阅产品；8002 是现有主动查询配置，订阅启用后不会用它轮询或自动兜底。
- 使用快递鸟同一账号下的真实用户 ID 和 API Key。校验回调通过不代表订阅套餐已开通，需确认 1008 权限、快递商覆盖范围、有效期及额度。
- 回调 URL 还必须在快递鸟控制台保存，并点击“校验成功提交”。程序中的此变量仅检查配置是否完整，不会替你登记控制台地址。`Callback` 是用户自定义回传信息，不是该 URL。
- 当前使用 HTTP 公网 IP，之后改用 HTTPS 时，两处地址都要修改。物流内容在 HTTP 下明文传输。
- 订阅产品填写后，若凭证或回调 URL 无效，应用和发布预检查会报错，避免静默切回主动查询。填写类型留空则使用手动查询模式。

```bash
chmod 600 /srv/shop/backend/.env
```

## 服务器前端配置

编辑 `/srv/shop/frontend/.env.local`：

```dotenv
NEXT_PUBLIC_API_URL=/api
NEXT_PUBLIC_AMAP_KEY=你的高德Web端JS_API_Key
NEXT_PUBLIC_AMAP_SECURITY_JS_CODE=你的高德安全密钥
```

物流密钥不放前端。保留已有高德配置；`/api` 由前端服务代理到后端，不能填写本地电脑的 localhost 地址。前端配置修改后需要重新构建前端镜像。

`/srv/shop/deploy.env` 只放部署参数，确认以下文件路径及本服务器项目设置，保留已有卷名：

```dotenv
SHOP_COMPOSE_PROJECT=app
SHOP_ENV_FILE=/srv/shop/backend/.env
SHOP_FRONTEND_ENV_FILE=/srv/shop/frontend/.env.local
SHOP_FRONTEND_BIND=0.0.0.0
```

不要整份覆盖 `deploy.env`，其中还有必须沿用的数据库卷和上传卷配置。

## 本地配置

本地 `backend/.env` 默认使用手动查询，下面两个值留空：

```dotenv
KDNIAO_SUBSCRIBE_REQUEST_TYPE=
KDNIAO_CALLBACK_URL=
```

可保留本地的商户 ID、API Key 和 `KDNIAO_REQUEST_TYPE=8002`，仅手动查询时调用服务商。只有在公网回调能进入本地、并且回调和订阅使用同一数据库的专门联调环境中，才在本地打开订阅模式。

## 自行推送与部署

本次代码、修复、模型和 migration 都需要提交，真实 `.env` 不要提交。特别包含新增的：

- `backend/shop_api/tracking_subscriptions.py`
- `backend/migrations/versions/20261027_04_tracking_subscriptions.py`
- `docs/tracking-webhook.md`

提交到 `dev` 后合并到 `main`，或按项目流程直接推送 `main`。`Test and deploy shop` 会自动构建、测试、备份数据库、执行 `alembic upgrade head`、重建 api/frontend。该服务器已执行 `20261027_04`，再次升级会保持该表，无需手工执行建表 SQL。

只有修改服务器后端配置、代码和数据库版本均不变时，可以仅重建 API 容器，让配置生效：

```bash
set -a
source /srv/shop/deploy.env
set +a
export SHOP_IMAGE_BASE=shop-release
export SHOP_IMAGE_TAG="$(cat /srv/shop/deployed-sha)"
shop_compose=(docker compose --env-file /srv/shop/deploy.env -f /srv/shop/current/compose.yml)
"${shop_compose[@]}" up -d --no-deps --pull never --force-recreate api
"${shop_compose[@]}" run --rm --no-deps --pull never api alembic current
curl --fail http://127.0.0.1:3000/api/tracking/subscription-options
```

预期 migration 为 `20261027_04`，配置接口返回 `{"enabled":true}`。这只说明本站启用了订阅，不代表服务商已受理运单。`docker restart` 不会重新加载修改后的 env_file，应使用上面的强制重建或重新运行 Actions。

修改前端配置，或有新代码时，完成提交合并后运行完整 Actions；不要用重启旧镜像代替构建新代码。

## 数据与可靠性

- 数据库以快递公司 + 单号唯一约束，所有用户对同一运单的重复登记只读记录。访问需要登录，仍采用原有“知道单号即可查询”的权限模型。
- 先落库订阅意图，再发送一次订阅请求。成功 active，明确拒绝 rejected，超时/协议异常 uncertain；进程在请求中退出会保留 pending。
- pending/uncertain/rejected 不自动重试，避免请求超时但服务商已受理时重复计费。管理员需先在快递鸟确认受理情况再决定是否重新登记；当前不提供前台重复提交入口。这是业务上的至多一次提交，不声称跨系统恰好一次。
- 回调验签基于原始 RequestData，校验商户并接受轨迹通知 RequestType 101 / 102。快递鸟控制台实测会为 1008 服务发送签名正确的 102 校验请求，不能按订阅产品严格限制回调类型。其他通知类型仍拒绝。全批次提交数据库成功后返回标准 Success 确认；数据库异常返回失败，由服务商按其规则重试。
- 回调最多 1MB / 100 单。先查本站已登记的运单；控制台未登记的样例运单只确认接收，不验证或保存业务字段。匹配到订阅的运单仍严格校验 Success、商户和轨迹字段，合并轨迹防止丢失；旧批次不覆盖新数据，重复批次不改更新时间。每单行锁防止并发覆盖。
- 保存轨迹中含有的配送资料，仅登录后凭单号读取；不在应用日志输出单号、原始回调和密钥。数据库及备份应按个人资料保护；当前保留记录，后续可按业务期限清理。
- “快递更新于”是最新物流节点发生时间；“本站同步于”是内容变化落库时间；“最近收到推送”是最近接受的新批次时间。重复/过期批次不会刷新这些时间。
- 页面刷新 / 点击查看只读取本地。已签收运单由快递鸟结束监控，本地继续展示最后轨迹。

## 上线验收

1. Actions 部署成功后打开公网商城，在同一台服务器的页面登录并登记一条真实运单。
2. “已订阅”说明服务商已受理；若“未获受理”，检查 1008 套餐权限和资料要求；若“待确认”，先去快递鸟确认受理情况，避免重复提交。
3. 运单发生更新后，在公网页面再次查看，确认“快递更新于”和“本站同步于”有值；后续查看只读数据库。
4. 控制台“校验通过”、模拟回调成功、真实运单成功是三个不同验收项。目前控制台校验已通过，仍需真实运单验收。

订阅只传 ShipperCode、LogisticCode、IsNotice=1（不通知上门）。如实际套餐要求寄收件资料，应补充发货登记数据；不要伪造资料来通过接口。

官方资料：[当前轨迹推送与回调配置](https://www.yuque.com/kdnjishuzhichi/dfcrg1/meiubz)、[标准订阅](https://www.kdniao.com/api-follow)、[增值订阅](https://www.kdniao.com/api-monitor)。以实际产品文档和账号权限为准。
