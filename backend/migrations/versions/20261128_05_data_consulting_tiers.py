"""Publish the three data consulting offerings in the existing catalog."""

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects.postgresql import insert

revision = "20261128_05"
down_revision = "20261027_04"
branch_labels = None
depends_on = None

COVER = "/images/data-consulting.webp"
OFFERINGS = (
    (
        "网页爬虫与数据采集服务", 2000, "采集约定来源的数据，一次性交付爬虫代码和采集结果",
        (
            "确认目标网站、页面类型、采集字段、时间区间和预计数据量，并约定采集范围。",
            "开发网页爬虫，按需采集允许访问的列表页、详情页和分页内容。",
            "将约定字段整理成结构化记录，按字段清单抽样核对采集结果。",
            "提供爬虫源代码和运行说明，按约定导出 CSV、Excel 或 JSON 格式的采集结果。",
        ),
    ),
    (
        "定制化数据咨询服务", 4000, "把已有数据整理成可核对的数据集、指标表和可视化图表",
        (
            "多表整合：合并用户提供的 Excel、CSV 或系统导出文件，统一字段、编码、日期和计量单位。",
            "清洗与质量检查：按约定规则去重、标记异常与缺失情况，核对跨表一致性，并交付问题清单。",
            "字段与指标说明：整理字段字典、计算口径和分组汇总表，便于复核和后续使用。",
            "描述性统计：提供频数、占比、分位数等汇总结果，按时间、分类或地区展示数据。",
            "可视化：按用途制作对比、趋势、分布图或轻量看板，并提供约定格式的图表与图注。",
            "可重复处理：为约定的整理步骤提供可重跑脚本或表格模板，并附交付文件及使用说明。",
        ),
    ),
    (
        "全流程数据服务与年度运维", 20000, "从研究设计和数据获取到分析建模、论文材料、工程交付和一年运维",
        (
            "需求与研究设计：梳理业务问题或研究假设，协助定义指标和变量、规划抽样与数据量、制定分析方案和验收标准。",
            "数据获取与追溯：接入约定网页、API、问卷、文件或数据库，支持历史补采和定时增量同步，记录来源、授权与版本。",
            "数据工程：设计数据表、数据字典和处理流程，配置任务调度、重试、日志、访问权限及约定的备份机制。",
            "数据治理与质量：执行去重、缺失及异常处理、口径对齐和跨源对账，按需做脱敏、质量校验及告警。",
            "统计分析：开展描述性统计、分组和趋势分析，按研究设计选用假设检验、置信区间、效应量或回归，并给出敏感性或稳健性检查。",
            "建模与算法：按项目目标完成特征构建、基线对比、训练验证、误差分析和调优，交付约定模型及评估记录。",
            "可视化与报告：制作交互看板、分析报告、论文级图表和可编辑图源，注明样本量、单位、指标口径及图注。",
            "论文写作支持：协助整理文献检索策略与证据表，梳理写作提纲及方法和结果部分，提供图表表达、引用格式和文字修改建议。",
            "可复现材料：交付授权范围内的数据、代码、依赖版本、运行步骤、数据字典及补充材料，便于复核图表和统计结果。",
            "部署与交接：通过 GitHub 仓库提交源代码、配置示例及开发文档，协助部署，提供使用培训和验收清单。",
            "一年运维：持续跟踪交付系统及数据质量，排查任务失败、数据偏差和程序缺陷，按约定修复、重跑或补数，并记录处理结果。",
        ),
    ),
)


def upgrade():
    products = sa.table(
        "products",
        sa.column("id"), sa.column("name"), sa.column("price"), sa.column("tagline"),
        sa.column("story"), sa.column("image_path"), sa.column("status"),
        schema="shop",
    )
    inventory = sa.table("inventory", sa.column("product_id"), sa.column("quantity"), schema="shop")
    connection = op.get_bind()

    for name, price, tagline, scope in OFFERINGS:
        statement = insert(products).values(
            name=name, price=price, tagline=tagline, story="\n".join(scope), image_path=COVER, status="listed",
        )
        product_id = connection.execute(
            statement.on_conflict_do_update(
                index_elements=[products.c.name],
                set_={
                    "price": statement.excluded.price,
                    "tagline": statement.excluded.tagline,
                    "story": statement.excluded.story,
                    "image_path": sa.func.coalesce(products.c.image_path, statement.excluded.image_path),
                },
            ).returning(products.c.id)
        ).scalar_one()
        connection.execute(
            insert(inventory).values(product_id=product_id, quantity=12).on_conflict_do_nothing(),
        )


def downgrade():
    # Retain catalog rows because carts, comments, and merchants may reference them.
    pass
