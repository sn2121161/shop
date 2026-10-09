"use client";

import Link from "next/link";
import { useParams } from "next/navigation";
import { useEffect, useState } from "react";
import { Button, Card, Descriptions, Result, Spin, Tag } from "antd";
import { api } from "../../shop";

type OrderItem = { name: string; quantity: number; unitPrice: number };
type Fulfillment = { deliveryService: string; recipientPhone?: string | null; province?: string | null; city?: string | null; district?: string | null; detail?: string | null; pickupStore?: string | null; pickupPhone?: string | null };
type Order = { id: number; total: number; customerAccount?: string | null; notificationStatus?: string | null; items: OrderItem[]; fulfillment?: Fulfillment | null };

function deliveryAddress(fulfillment: Fulfillment) {
  if (fulfillment.pickupStore) return fulfillment.pickupStore;
  return [fulfillment.province, fulfillment.city, fulfillment.district, fulfillment.detail].filter(Boolean).join("");
}

export default function OrderPage() {
  const { id } = useParams<{ id: string }>();
  const [order, setOrder] = useState<Order>();
  useEffect(() => { void api.get<Order>(`/orders/${id}`).then(({ data }) => setOrder(data)); }, [id]);
  if (!order) return <div className="loading"><Spin /></div>;
  const fulfillment = order.fulfillment;
  const notification = order.notificationStatus === "notified" ? <Tag color="green">飞书已通知</Tag> : <Tag color="gold">飞书通知待重试</Tag>;
  return <main className="order-page">
    <Result status="success" title="订单已创建" subTitle={`订单 #${order.id}，应付 ¥ ${order.total.toFixed(2)}。目前不提供线上支付跳转。`} extra={<Link href="/"><Button type="primary">回到小屋</Button></Link>} />
    <Card title="本次订单" extra={notification}>
      <Descriptions column={1} size="middle" labelStyle={{ width: 112, color: "#667085" }}>
        <Descriptions.Item label="订单号">#{order.id}</Descriptions.Item>
        <Descriptions.Item label="购买商品">{order.items.map((item) => <div key={item.name}>{item.name} × {item.quantity}</div>)}</Descriptions.Item>
        <Descriptions.Item label="下单账号">{order.customerAccount || "—"}</Descriptions.Item>
        <Descriptions.Item label="手机号">{fulfillment?.recipientPhone || fulfillment?.pickupPhone || "—"}</Descriptions.Item>
        <Descriptions.Item label="配送服务">{fulfillment?.deliveryService || "—"}</Descriptions.Item>
        {fulfillment && <Descriptions.Item label={fulfillment.pickupStore ? "自提点" : "配送地址"}>{deliveryAddress(fulfillment)}</Descriptions.Item>}
      </Descriptions>
    </Card>
  </main>;
}
