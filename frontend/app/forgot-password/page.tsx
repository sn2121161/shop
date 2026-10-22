"use client";

import { Button, Card, Form, Input, message } from "antd";
import { api, apiErrorMessage } from "../shop";

type ForgotPasswordForm = { email: string };

export default function ForgotPassword() {
  const [notice, holder] = message.useMessage();
  const submit = async (values: ForgotPasswordForm) => {
    try {
      const { data } = await api.post<{ message: string }>("/auth/forgot-password", values);
      notice.success(data.message);
    } catch (error: unknown) {
      notice.error(apiErrorMessage(error, "发送失败，请稍后重试"));
    }
  };
  return <main className="auth-page">
    {holder}<Card className="auth-card"><a className="back-home" href="/login">← 返回登录</a>
      <p className="eyebrow">PASSWORD RESET</p><h1>找回密码</h1><p>输入注册邮箱，我们会发送有效期 30 分钟的密码重置链接。</p>
      <Form layout="vertical" onFinish={submit}>
        <Form.Item label="注册邮箱" name="email" rules={[{ required: true, message: "请输入邮箱" }, { type: "email", message: "请输入有效的邮箱地址" }]}><Input size="large" type="email" autoComplete="email" /></Form.Item>
        <Button block size="large" type="primary" htmlType="submit">发送重置链接</Button>
      </Form>
    </Card>
  </main>;
}
