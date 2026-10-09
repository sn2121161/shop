import type { Metadata } from "next";
import "./globals.css";
export const metadata: Metadata = { title: "我的神秘小屋 · 分子项链", description: "把有机化学分子的优雅结构，变成可以佩戴的手作项链。" };
export default function RootLayout({children}:{children:React.ReactNode}) { return <html lang="zh-CN"><body>{children}</body></html>; }
