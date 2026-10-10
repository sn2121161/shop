"use client";

import { useEffect, useMemo, useRef, useState, useSyncExternalStore } from "react";
import Link from "next/link";
import { Button, Card, Empty, Input, Layout, Tag, message } from "antd";
import { gsap } from "gsap";
import { ShoppingBag, Sparkles, Search, ArrowRight, Atom, UserRound } from "lucide-react";
import { api, productImage, type Product, useShop } from "./shop";

const { Header, Content, Footer } = Layout;
const emptySubscribe = () => () => {};

function useHydrated() {
  return useSyncExternalStore(emptySubscribe, () => true, () => false);
}

function Topbar() {
  const { cartCount, token, username, role, clearSession } = useShop();
  return <Header className="topbar" data-gsap="topbar">
    <Link href="/" className="brand"><span className="brand-mark">M</span><span>我的神秘小屋</span></Link>
    <nav><a href="#story">灵感</a><a href="#collection">项链系列</a><a href="#notice">创作说明</a></nav>
    <div className="header-actions">
      {token ? <><span className="account-indicator" title={`当前登录账号：${username || "加载中"}`}><UserRound size={16}/><span>{username || "加载中"}</span></span>{role === "admin" && <a href="/admin">管理后台</a>}<Button type="text" onClick={clearSession}>退出登录</Button></> : <><a href="/login">登录</a><a href="/register"><Button type="primary">注册</Button></a></>}
      <a href="/cart" className="cart-link"><ShoppingBag size={18}/><span>购物车</span><b>{cartCount}</b></a>
    </div>
  </Header>;
}

export default function Home() {
  const hydrated = useHydrated();
  const pageRef = useRef<HTMLDivElement>(null);
  const [products, setProducts] = useState<Product[]>([]); const [keyword, setKeyword] = useState("");
  const { token, refreshCart, hydrate } = useShop(); const [notice, contextHolder] = message.useMessage();
  useEffect(() => { queueMicrotask(() => { void hydrate(); }); }, [hydrate]);
  useEffect(() => { api.get<Product[]>("/products").then(({ data }) => setProducts(data)).catch(() => notice.error("暂时无法取得商品资料")); }, [notice]);
  useEffect(() => {
    if (!hydrated || window.matchMedia("(prefers-reduced-motion: reduce)").matches) return;
    const context = gsap.context(() => {
      const timeline = gsap.timeline({ defaults: { ease: "power2.out" } });
      timeline.from('[data-gsap="topbar"]', { y: -20, autoAlpha: 0, duration: 0.45 })
        .from('[data-gsap="hero-copy"] > *', { y: 24, autoAlpha: 0, duration: 0.55, stagger: 0.08 }, "-=0.15")
        .from('[data-gsap="hero-image"]', { scale: 0.96, autoAlpha: 0, duration: 0.7 }, "-=0.35")
        .from('[data-gsap="story"]', { y: 26, autoAlpha: 0, duration: 0.55 }, "-=0.2");
    }, pageRef);
    return () => context.revert();
  }, [hydrated]);
  useEffect(() => {
    if (!hydrated || !products.length || window.matchMedia("(prefers-reduced-motion: reduce)").matches) return;
    const context = gsap.context(() => {
      gsap.from('[data-gsap="product-card"]', { y: 24, autoAlpha: 0, duration: 0.45, stagger: 0.06, ease: "power2.out", clearProps: "transform" });
    }, pageRef);
    return () => context.revert();
  }, [hydrated, products.length]);
  const shown = useMemo(() => products.filter((p) => `${p.name}${p.tagline}`.includes(keyword.trim())), [products, keyword]);
  const addCart = async (product: Product) => {
    if (!token) { notice.info("登录后即可将作品加入购物车"); return; }
    try { await api.post("/cart", { productId: product.id, quantity: 1 }); await refreshCart(); notice.success("已加入购物车"); } catch { notice.error("加入购物车失败，请稍后再试"); }
  };
  if (!hydrated) return <div className="site-shell" aria-busy="true" />;
  return <div ref={pageRef}><Layout className="site-shell">{contextHolder}<Topbar/><Content>
    <section className="hero"><div className="hero-copy" data-gsap="hero-copy"><p className="eyebrow"><Sparkles size={15}/> MOLECULE JEWELRY / 01</p><h1 className="hero-title"><span>把 看不见的</span><span><em>分子</em> 戴在</span><span><em>身上</em></span></h1><p className="hero-lede">我的神秘小屋，收集有机化学里那些优雅的连接方式。每一条项链从分子结构出发，在手作的温度里成为一段可以佩戴的故事。</p><a className="primary-link" href="#collection">探索分子系列 <ArrowRight size={18}/></a></div><div className="hero-image" data-gsap="hero-image"><img src="/images/design.jpg" alt="分子项链设计图" width={640} height={530}/><div className="image-note">手作设计档案<br/><strong>来自实验与想象</strong></div></div></section>
    <section id="story" className="story-grid" data-gsap="story"><div className="story-image"><img src="/images/draft.jpg" alt="分子项链草稿手绘" width={640} height={550}/></div><div className="story-copy"><p className="eyebrow">THE FIRST SKETCH</p><h2>从一页草稿，<br/>到一条项链。</h2><p>化学式并不冷冰冰。它们有相遇、分岔、闭合，也有恰到好处的留白。我把这些微观的秩序画成草图，再一根根弯折、连接，让它们在颈间拥有新的尺度。</p><p>这里的每件作品都是对科学图谱的视觉致意：不售卖任何化学物质，只分享结构、手艺与好奇心。</p><Tag color="gold">化学结构艺术饰品</Tag></div></section>
    <section id="collection" className="collection"><div className="section-heading"><div><p className="eyebrow">THE COLLECTION / 17 PIECES</p><h2>分子项链系列</h2><p>每一种结构，都是一个安静而独特的符号。</p></div><Input prefix={<Search size={17}/>} placeholder="搜索分子名称或灵感" value={keyword} onChange={(e) => setKeyword(e.target.value)} className="search-box" allowClear/></div>
      {shown.length ? <div className="product-grid">{shown.map((product) => <Card className="product-card" data-gsap="product-card" key={product.id} cover={<a href={`/products/${product.id}`}><div className="product-image"><img src={productImage(product)} alt={`${product.name} 项链`} width={300} height={260}/><span>查看作品</span></div></a>}><div className="product-meta"><div><h3>{product.name}</h3><p>{product.tagline}</p>{product.lowStock && <em className="low-stock">仅剩 {product.stock} 件</em>}</div><strong>¥ {product.price}</strong></div><div className="product-actions"><a href={`/products/${product.id}`}>阅读故事</a><Button disabled={!product.stock} onClick={() => addCart(product)}>{product.stock ? "加入购物车" : "暂时售罄"}</Button></div></Card>)}</div> : <Empty description="没有找到相应的分子作品"/>}</section>
    <section id="notice" className="notice"><Atom size={34}/><div><h3>关于这组作品</h3><p>部分名称来自受管制物质的分子结构，仅用于化学结构艺术研究与首饰设计；本店不提供、推广或讨论任何物质的获取与使用。</p></div></section>
  </Content><Footer>我的神秘小屋 · 分子项链 — 以好奇心为线，以结构为形</Footer></Layout></div>;
}
