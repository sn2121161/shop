"use client";

/* eslint-disable @next/next/no-html-link-for-pages -- Native navigation avoids the current Vinext Link RSC runtime error. */

import { useRouter } from "next/navigation";
import { Button, Card, Form, Input, message } from "antd";
import { api, apiErrorMessage } from "../shop";

type RegisterForm = { username: string; email: string; password: string; confirmPassword: string };

export default function Register() {
  const router = useRouter();
  const [form] = Form.useForm();
  const [notice, holder] = message.useMessage();
  const submit = async (values: RegisterForm) => {
    try {
      await api.post("/auth/register", values);
      notice.success("注册成功，请登录");
      router.push("/login");
    } catch (error: unknown) {
      notice.error(apiErrorMessage(error, "注册失败"));
    }
  };
  return <main className="auth-page">
    {holder}<Card className="auth-card"><a className="back-home" href="/">← 回到小屋</a>
      <p className="eyebrow">JOIN THE STORY</p><h1>创建账户</h1><p>将喜欢的分子故事收藏进你的购物车。</p>
      <Form form={form} layout="vertical" onFinish={submit}>
        <Form.Item label="账号" name="username" rules={[{ required: true, message: "请输入账号" }, { min: 3, message: "至少 3 位" }]}><Input size="large" /></Form.Item>
        <Form.Item label="邮箱" name="email" rules={[{ required: true, message: "请输入邮箱" }, { type: "email", message: "请输入有效的邮箱地址" }]}><Input size="large" type="email" autoComplete="email" /></Form.Item>
        <Form.Item label="密码" name="password" extra="至少 9 位，含大小写字母、数字和特殊字符" rules={[{ required: true, message: "请输入密码" }]}><Input.Password size="large" /></Form.Item>
        <Form.Item label="确认密码" name="confirmPassword" dependencies={["password"]} rules={[
          { required: true, message: "请再次输入密码" },
          ({ getFieldValue }) => ({ validator(_, value) { return !value || getFieldValue("password") === value ? Promise.resolve() : Promise.reject(new Error("两次密码不一致")); } }),
        ]}><Input.Password size="large" /></Form.Item>
        <Button block size="large" type="primary" htmlType="submit">创建账户</Button>
      </Form><p className="auth-switch">已有账号？ <a href="/login">去登录</a></p>
    </Card>
  </main>;
}
