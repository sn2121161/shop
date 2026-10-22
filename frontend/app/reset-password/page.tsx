"use client";

import { useRouter, useSearchParams } from "next/navigation";
import { Button, Card, Form, Input, message } from "antd";
import { api, apiErrorMessage } from "../shop";

type ResetPasswordForm = { newPassword: string; confirmPassword: string };

export default function ResetPassword() {
  const router = useRouter();
  const params = useSearchParams();
  const [notice, holder] = message.useMessage();
  const token = params.get("token");
  const submit = async (values: ResetPasswordForm) => {
    if (!token) { notice.error("重置链接无效或已过期，请重新申请"); return; }
    try {
      const { data } = await api.post<{ message: string }>("/auth/reset-password", { ...values, token });
      notice.success(data.message);
      router.push("/login");
    } catch (error: unknown) {
      notice.error(apiErrorMessage(error, "密码重置失败"));
    }
  };
  return <main className="auth-page">
    {holder}<Card className="auth-card"><a className="back-home" href="/login">← 返回登录</a>
      <p className="eyebrow">NEW PASSWORD</p><h1>设置新密码</h1><p>新密码将使该账号此前的登录状态失效。</p>
      <Form layout="vertical" onFinish={submit}>
        <Form.Item label="新密码" name="newPassword" extra="至少 9 位，含大小写字母、数字和特殊字符" rules={[{ required: true, message: "请输入新密码" }]}><Input.Password size="large" autoComplete="new-password" /></Form.Item>
        <Form.Item label="确认新密码" name="confirmPassword" dependencies={["newPassword"]} rules={[{ required: true, message: "请再次输入新密码" }, ({ getFieldValue }) => ({ validator(_, value) { return !value || getFieldValue("newPassword") === value ? Promise.resolve() : Promise.reject(new Error("两次密码不一致")); } })]}><Input.Password size="large" autoComplete="new-password" /></Form.Item>
        <Button block size="large" type="primary" htmlType="submit">重置密码</Button>
      </Form>
    </Card>
  </main>;
}
