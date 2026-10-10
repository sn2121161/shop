"use client";

import { useRouter } from "next/navigation";
import { Button, Card, Form, Input, message } from "antd";
import { api, apiErrorMessage, useShop } from "../shop";

type LoginForm = { username: string; password: string };
type LoginResponse = { token: string; user: { username: string; role: string } };

export default function Login() {
  const router = useRouter();
  const { setSession, refreshCart } = useShop();
  const [notice, holder] = message.useMessage();
  const submit = async (values: LoginForm) => {
    try {
      const { data } = await api.post<LoginResponse>("/auth/login", values);
      setSession(data.token, data.user.username, data.user.role);
      if (data.user.role !== "admin") await refreshCart();
      notice.success("欢迎回来");
      router.push(data.user.role === "admin" ? "/admin" : "/");
    } catch (error: unknown) {
      notice.error(apiErrorMessage(error, "登录失败"));
    }
  };
  return <main className="auth-page">{holder}<Card className="auth-card"><a className="back-home" href="/">← 回到小屋</a><p className="eyebrow">WELCOME BACK</p><h1>登录小屋</h1><p>登录后即可保存心仪的分子项链。</p><Form layout="vertical" onFinish={submit}><Form.Item label="账号" name="username" rules={[{ required: true, message: "请输入账号" }]}><Input size="large" /></Form.Item><Form.Item label="密码" name="password" rules={[{ required: true, message: "请输入密码" }]}><Input.Password size="large" /></Form.Item><Button block size="large" type="primary" htmlType="submit">登录</Button></Form><p className="auth-switch">还没有账号？ <a href="/register">现在注册</a></p></Card></main>;
}
