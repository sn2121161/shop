"use client";

import { useEffect, useMemo, useState } from "react";
import { Button, Card, DatePicker, Empty, Input, Select, Space, Spin, Statistic, Table, Tag } from "antd";
import { api, apiErrorMessage } from "../shop";

type DateRange = { start: string; end: string };
type Dashboard = {
  summary: { todayOrders: number; todaySales: number; totalSales: number; activeUsers: number; listedProducts: number; outOfStockProducts: number; lowStockProducts: number };
  trend: { date: string; orders: number; sales: number }[];
  users: { username: string; orderCount: number; unitsBought: number; sales: number }[];
  products: { product: string; unitsSold: number; sales: number; currentStock: number | null }[];
  details: { items: { id: number; createdAt: string; username: string; deliveryService: string; total: number; items: { name: string; quantity: number; currentStock: number | null }[] }[]; total: number; page: number; pageSize: number };
};

const dayString = (offset: number) => { const value = new Date(); value.setHours(0, 0, 0, 0); value.setDate(value.getDate() + offset); return value.toLocaleDateString("en-CA"); };

function TrendChart({ rows }: { rows: Dashboard["trend"] }) {
  const bars = useMemo(() => {
    const max = Math.max(1, ...rows.map((row) => row.orders));
    const column = 90 / Math.max(rows.length, 1);
    const width = Math.max(0.8, Math.min(3.2, column * 0.58));
    return rows.map((row, index) => {
      const height = row.orders ? (row.orders / max) * 66 : 0;
      return { ...row, x: 5 + index * column + (column - width) / 2, y: 88 - height, height, width };
    });
  }, [rows]);
  if (!rows.length) return <Empty image={Empty.PRESENTED_IMAGE_SIMPLE} description="所选日期暂无订单" />;
  return <div className="dashboard-chart"><svg viewBox="0 0 100 100" preserveAspectRatio="none" role="img" aria-label="每日下单趋势柱状图"><line x1="5" x2="95" y1="22" y2="22" className="dashboard-guide" /><line x1="5" x2="95" y1="55" y2="55" className="dashboard-guide" /><line x1="5" x2="95" y1="88" y2="88" className="dashboard-baseline" />{bars.map((bar) => bar.height > 0 && <rect key={bar.date} x={bar.x} y={bar.y} width={bar.width} height={bar.height} rx="0.8" className="dashboard-bar"><title>{`${bar.date}：${bar.orders} 单，销售额 ¥${bar.sales.toFixed(2)}`}</title></rect>)}</svg><div className="dashboard-axis"><span>{rows[0].date.slice(5)}</span><span>{rows[Math.floor(rows.length / 2)].date.slice(5)}</span><span>{rows.at(-1)?.date.slice(5)}</span></div></div>;
}

export default function DashboardPanel() {
  const [period, setPeriod] = useState("30"); const [custom, setCustom] = useState<DateRange | undefined>(); const [filters, setFilters] = useState({ username: "", product: "", delivery: "" }); const [page, setPage] = useState(1); const [data, setData] = useState<Dashboard>(); const [loading, setLoading] = useState(true); const [error, setError] = useState("");
  const range = useMemo(() => period === "custom" && custom ? custom : { start: dayString(-((period === "custom" ? 30 : Number(period)) - 1)), end: dayString(0) }, [period, custom]);
  const load = async (targetPage = page) => { const params = new URLSearchParams({ ...range, page: String(targetPage) }); if (filters.username) params.set("username", filters.username); if (filters.product) params.set("product", filters.product); if (filters.delivery) params.set("delivery_service", filters.delivery); setLoading(true); setError(""); try { setData((await api.get<Dashboard>(`/admin/dashboard?${params}`)).data); } catch (requestError) { setError(apiErrorMessage(requestError, "管理看板加载失败，请检查后端服务后重试")); } finally { setLoading(false); } };
  useEffect(() => { const timer = window.setTimeout(() => void load(1), 0); return () => window.clearTimeout(timer); // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [range.start, range.end]);
  if (!data) return <Card>{loading ? <div className="dashboard-loading"><Spin size="large" tip="正在汇总经营数据…" /></div> : <Empty description={error || "管理看板加载失败"} image={Empty.PRESENTED_IMAGE_SIMPLE}><Button type="primary" onClick={() => void load(1)}>重新加载</Button></Empty>}</Card>;
  const cards = [["当日下单量", data.summary.todayOrders, "单"], ["当日销售额", data.summary.todaySales, "¥"], ["累计销售额", data.summary.totalSales, "¥"], ["启用用户", data.summary.activeUsers, "人"], ["上架商品", data.summary.listedProducts, "件"], ["缺货商品", data.summary.outOfStockProducts, "件"], ["低库存商品", data.summary.lowStockProducts, "件"]];
  const detailColumns = [{ title: "订单", dataIndex: "id", render: (value: number) => `#${value}` }, { title: "下单用户", dataIndex: "username" }, { title: "售出商品", render: (_: unknown, row: Dashboard["details"]["items"][number]) => row.items.map((item) => <div key={item.name}>{item.name} × {item.quantity} <small>库存 {item.currentStock ?? "—"}</small></div>) }, { title: "配送", dataIndex: "deliveryService" }, { title: "金额", dataIndex: "total", render: (value: number) => `¥ ${value.toFixed(2)}` }, { title: "时间", dataIndex: "createdAt", render: (value: string) => new Intl.DateTimeFormat("zh-CN", { dateStyle: "short", timeStyle: "short" }).format(new Date(value)) }];
  return <div className="dashboard-panel"><Card className="dashboard-filter"><Space wrap><span>统计周期</span>{["7", "30", "90"].map((value) => <Button key={value} type={period === value ? "primary" : "default"} onClick={() => { setPeriod(value); setPage(1); }}>{`近 ${value} 天`}</Button>)}<Button type={period === "custom" ? "primary" : "default"} onClick={() => setPeriod("custom")}>自定义</Button>{period === "custom" && <DatePicker.RangePicker onChange={(value) => setCustom(value?.[0] && value?.[1] ? { start: value[0].format("YYYY-MM-DD"), end: value[1].format("YYYY-MM-DD") } : undefined)} />}</Space></Card><section className="metric-grid">{cards.map(([title, value, prefix]) => <Card key={String(title)}><Statistic title={title as string} value={value as number} prefix={prefix === "¥" ? "¥" : undefined} suffix={prefix === "¥" ? undefined : prefix as string} precision={prefix === "¥" ? 2 : 0} /></Card>)}</section><section className="dashboard-two-column"><Card title="每日下单趋势" extra={<Tag color="green">{data.trend.reduce((sum, row) => sum + row.orders, 0)} 单</Tag>}><TrendChart rows={data.trend} /></Card><Card title="商品售出排行"><Table size="small" rowKey="product" pagination={false} dataSource={data.products.slice(0, 6)} columns={[{ title: "商品", dataIndex: "product" }, { title: "售出", dataIndex: "unitsSold", render: (value: number) => `${value} 件` }, { title: "销售额", dataIndex: "sales", render: (value: number) => `¥ ${value.toFixed(2)}` }, { title: "当前库存", dataIndex: "currentStock", render: (value: number | null) => value === null ? "—" : value <= 5 ? <span className="admin-low-stock">仅剩 {value} 件</span> : value }]} /></Card></section><section className="dashboard-two-column"><Card title="用户下单统计"><Table size="small" rowKey="username" pagination={false} dataSource={data.users.slice(0, 6)} columns={[{ title: "用户", dataIndex: "username" }, { title: "订单", dataIndex: "orderCount" }, { title: "件数", dataIndex: "unitsBought" }, { title: "消费额", dataIndex: "sales", render: (value: number) => `¥ ${value.toFixed(2)}` }]} /></Card><Card title="库存提醒"><div className="stock-summary"><Tag color="red">缺货 {data.summary.outOfStockProducts} 件</Tag><Tag color="volcano">低库存 {data.summary.lowStockProducts} 件</Tag><p>库存数为实时库存，用于补货判断。</p></div></Card></section><Card title="订单销售明细" className="dashboard-details"><Space className="admin-filters" wrap><Input placeholder="下单账号" value={filters.username} onChange={(event) => setFilters({ ...filters, username: event.target.value })} /><Input placeholder="商品名称" value={filters.product} onChange={(event) => setFilters({ ...filters, product: event.target.value })} /><Select placeholder="配送方式" allowClear value={filters.delivery || undefined} onChange={(value) => setFilters({ ...filters, delivery: value || "" })} options={["线下自提", "顺丰次日达", "圆通快递", "国通快递", "申通快递", "韵达快递"].map((value) => ({ value, label: value }))} /><Button type="primary" onClick={() => { setPage(1); void load(1); }}>筛选</Button></Space><Table rowKey="id" scroll={{ x: 860 }} columns={detailColumns} dataSource={data.details.items} pagination={{ current: data.details.page, total: data.details.total, pageSize: data.details.pageSize, onChange: (next) => { setPage(next); void load(next); } }} /></Card></div>;
}
