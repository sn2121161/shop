# 从零搭建商城后端：环境准备提示词清单

> 给学员：这份清单参考“分子项链商城”现有后端，帮助你在自己的电脑上搭建同一类后端技术环境。你可以设计自己的商品、页面和前端。每次把“通用提示词”与对应步骤的提示词一起发给 AI，先检查，再安装，最后验证。

## 一、先分清要装什么

| 类别 | 要准备的内容 | 它负责什么 | 如何验证 |
|---|---|---|---|
| 电脑上的工具 | Git | 保存代码版本，便于回退和协作 | `git --version` |
| 电脑上的工具 | uv 与 Python 3.10 | 安装 Python、创建独立环境、安装并运行 Python 包 | `uv --version`、`uv run python --version` |
| 独立运行的软件 | PostgreSQL | 长期保存用户、商品、购物车、订单等数据 | `psql --version`，并确认数据库服务可连接 |
| 项目里的 Python 包 | FastAPI、Uvicorn 等 | 提供接口、处理业务、访问数据库、运行测试 | `uv run python -c "import fastapi, sqlalchemy, psycopg2"` |

**容易混淆的地方**：FastAPI 是由 uv 安装在项目里的 Python 包，不是需要单独下载的桌面软件；PostgreSQL 则需要单独安装并启动数据库服务。现有项目使用 FastAPI，而不是 Flask。这个后端不要求学员使用特定的前端框架，也不要求安装 Node.js、pnpm 或飞书客户端。

## 二、通用提示词（每一步都可附上）

> 我想从零创建自己的商城后端，参考分子项链商城的后端技术选型：Python 3.10、uv、FastAPI、Uvicorn、SQLAlchemy、PostgreSQL。请先识别我的操作系统和当前目录，再检查已有工具。只给适合我系统的安装步骤；每一步都写出检查命令、成功标志和常见错误的处理方法。不要假设我已经有老师的项目、Conda 环境或某一种前端。请先完成环境准备，不替我生成完整业务代码。

## 三、逐项安装与提示词

### 1. Git：管理自己的代码

Git 用来记录“这次修改了什么”和“需要回到哪个版本”。先运行 `git --version`；没有安装时，按 [Git 官方安装页](https://git-scm.com/install/) 选择自己的系统。新建自己的项目目录后，可用 `git init` 开始版本管理。是否上传到代码托管平台由课程安排决定，不需要现成的商城仓库地址。

**提示词 1｜安装 Git**

> 我的操作系统是【填写系统】。请先指导我检查 Git；如果没有安装，给出官方安装入口和适合本机的步骤。安装后让我验证版本，并在我新建的商城项目目录里初始化 Git。解释 `git status`、`git add`、`git commit` 分别做什么；不要要求我克隆老师的项目。

### 2. uv 与 Python：准备后端运行环境

uv 负责下载 Python、创建项目专用环境和安装依赖。先检查 `uv --version`；没有安装时使用 [uv 官方安装说明](https://docs.astral.sh/uv/getting-started/installation/)。参考项目在 Python 3.10 上运行过，学员先用同一主版本。无需复制老师的 `firstenv` 环境。

从零创建后端目录的参考命令：

```bash
uv python install 3.10
uv init --bare --python 3.10 backend
cd backend
uv python pin 3.10
uv run python --version
```

`uv init --bare` 会创建记录项目依赖的 `pyproject.toml`；`uv python pin 3.10` 会把项目使用的 Python 主版本记录在 `.python-version`；后续 `uv add` 会将依赖写入项目文件。若目录已存在或本机命令与示例不符，让 AI 先查看现状再调整，不要覆盖已有文件。相关说明见 [uv 项目文档](https://docs.astral.sh/uv/guides/projects/)。

**提示词 2｜安装 uv 与 Python**

> 请先检查本机是否有 uv 和 Python 3.10。缺少 uv 时给出官方安装步骤；然后指导我用 uv 安装 Python 3.10，并在我自己的项目目录创建 `backend` Python 项目，用 `uv python pin 3.10` 固定项目主版本。请解释“Python 解释器”“项目环境”“pyproject.toml”这三个词各自是什么意思。逐步验证 uv 运行的确实是项目使用的 Python；若目录已经存在，先检查再给命令。

### 3. PostgreSQL：准备能长期保存数据的数据库

PostgreSQL 是独立运行的数据库软件。`psql --version` 只能证明命令行客户端存在；还要确认数据库服务已启动，并能用本机账号连接。按 [PostgreSQL 官方下载页](https://www.postgresql.org/download/) 选择安装方式。学员创建自己的商城数据库；数据库名和账号由学员自己决定。这个项目的表结构是用 SQLAlchemy 描述的，最终数据存入 PostgreSQL。

**提示词 3｜安装数据库**

> 请指导我检查 PostgreSQL 客户端、数据库服务和本机连接是否可用。若缺少，给出官方安装入口及适合我操作系统的步骤。然后指导我创建一个供自己商城使用的数据库，验证我能连接，并解释“数据库”“表”“主键”“外键”各是什么意思。这里只检查软件与数据库是否准备好，暂时不要设计具体业务表，也不要写任何环境变量配置。

### 4. 安装后端 Python 包

参考项目的依赖记录在 `backend/requirements.txt`。从零创建自己的后端时，可以用 uv 将这些包装进自己的项目；不需要逐个去网页下载安装。建议先装基础部分，再按准备实现的功能补充其余部分。下面的版本是当前分子项链商城后端使用的版本，创建新项目时可以先以此为参考。

| 功能 | 包 | 简单作用 |
|---|---|---|
| 接口与启动 | `fastapi==0.128.0`、`uvicorn[standard]==0.40.0` | 接收请求、返回结果、启动服务 |
| 数据库 | `SQLAlchemy==2.0.45`、`psycopg2-binary==2.9.11` | 用 Python 描述和操作数据表，连接 PostgreSQL |
| 注册与登录 | `PyJWT==2.11.0`、`Werkzeug==3.1.4` | 制作登录凭证、处理密码摘要 |
| 商品评论与图片 | `bleach==6.3.0`、`python-multipart==0.0.22` | 清理评论内容、接收上传文件 |
| 银行卡资料保护 | `cryptography==46.0.3` | 加密项目中的模拟银行卡资料；它本身不提供真实收款 |
| 外部通知 | `httpx==0.28.1` | 向飞书等外部接口发送请求；只做基础商城时可暂缓接入通知功能 |
| 本地配置读取 | `python-dotenv==1.2.1` | 读取项目本地配置文件；此清单不讲配置内容 |
| 自动测试 | `pytest==9.0.2`、`httpx==0.28.1` | 检查接口和业务行为；`httpx` 同时可用于测试接口 |

在 `backend/` 目录下，先安装接口和数据库所需的包：

```bash
uv add "fastapi==0.128.0" "uvicorn[standard]==0.40.0" "SQLAlchemy==2.0.45" "psycopg2-binary==2.9.11"
```

需要复刻参考项目的注册登录、评论上传、模拟银行卡、飞书通知和本地配置读取时，再安装其余运行依赖：

```bash
uv add "PyJWT==2.11.0" "Werkzeug==3.1.4" "bleach==6.3.0" "python-multipart==0.0.22" "cryptography==46.0.3" "httpx==0.28.1" "python-dotenv==1.2.1"
uv add --dev "pytest==9.0.2"
```

**提示词 4｜安装项目依赖**

> 我已经用 uv 创建了新的 `backend` 项目。请按“接口与启动、数据库、注册登录、评论上传、银行卡资料保护、外部通知、自动测试”分组，检查分子项链商城 `backend/requirements.txt` 中的包。先指导我用 `uv add` 安装 FastAPI、Uvicorn、SQLAlchemy、PostgreSQL 驱动，再按我要实现的功能安装对应包，测试工具放入开发依赖。不要让我全局安装 FastAPI，也不要把“安装 Python 包”和“安装 PostgreSQL 服务”混为一谈。每组安装后给一条能验证导入成功的命令。

### 5. 验收：确认技术环境已经就绪

环境准备完成后，可在 `backend/` 检查 `uv run python --version`、`uv run python -c "import fastapi, sqlalchemy, psycopg2"`，并检查 PostgreSQL 服务能连接。以后写好应用入口，再用 `uv run uvicorn app:app --reload --port 5600` 本地启动；写好测试后，用 `uv run pytest -q` 验证。此时如果还没有业务代码，启动命令找不到 `app.py` 是正常的，不能把它当成安装失败。

**提示词 5｜环境验收**

> 请为我制作一张后端环境验收表，只检查 Git、uv、Python 3.10、PostgreSQL 服务，以及已经安装的 FastAPI、Uvicorn、SQLAlchemy、PostgreSQL 驱动和我选择的其他 Python 包。每项给出一条检查命令、预期结果和失败时的下一步。我的业务代码可能还没写，所以不要以页面能打开或完整商城能下单作为环境安装成功的条件。

## 四、学员填写的检查记录

| 检查项 | 我的检查结果 | 缺少时怎么获得 | 最终是否通过 |
|---|---|---|---|
| Git |  | [官方安装页](https://git-scm.com/install/) |  |
| uv 与 Python 3.10 |  | [uv 官方安装页](https://docs.astral.sh/uv/getting-started/installation/) |  |
| PostgreSQL 服务 |  | [官方下载安装页](https://www.postgresql.org/download/) |  |
| FastAPI 与 Uvicorn |  | 在 `backend/` 用 `uv add` 安装 |  |
| SQLAlchemy 与 PostgreSQL 驱动 |  | 在 `backend/` 用 `uv add` 安装 |  |
| 我选择的其他功能包 |  | 参照上表用 `uv add` 安装 |  |

> 这份清单只回答“从零搭建后端需要什么环境、怎样安装、怎样检查”。商品、订单、数据库表和接口的设计，请使用课程的后端功能提示词文档。
