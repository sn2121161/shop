"use client";

/* eslint-disable @next/next/no-html-link-for-pages -- Native navigation avoids the current Vinext Link RSC runtime error. */

import { useParams } from "next/navigation";
import { useEffect, useState } from "react";
import { Button, Divider, InputNumber, Spin, Tag, message } from "antd";
import { ArrowLeft, Home, ShoppingBag } from "lucide-react";
import { api, apiErrorMessage, productImage, productReferenceImage, Product, useShop } from "../../shop";
import ProductComments from "../../components/ProductComments";
import MoleculeCard from "../../components/MoleculeCard";

export default function ProductPage() {
  const { id } = useParams<{ id: string }>();
  const [product, setProduct] = useState<Product>();
  const [loadError, setLoadError] = useState("");
  const [attempt, setAttempt] = useState(0);
  const [quantity, setQuantity] = useState(1);
  const { token, refreshCart, hydrate } = useShop();
  const [notice, holder] = message.useMessage();
  useEffect(() => { hydrate(); }, [hydrate]);
  useEffect(() => {
    if (!id) return;
    let active = true;
    api.get<Product>(`/products/${id}`).then(({ data }) => {
      if (active) { setProduct(data); setLoadError(""); }
    }).catch((error: unknown) => {
      if (active) setLoadError(apiErrorMessage(error, "商品详情暂时无法加载，请稍后重试"));
    });
    return () => { active = false; };
  }, [id, attempt]);
  const add = async () => {
    if (!token) { notice.info("登录后即可加入购物车"); return; }
    try { await api.post("/cart", { productId: product!.id, quantity }); await refreshCart(); notice.success(`已加入购物车 × ${quantity}`); }
    catch (error: unknown) { notice.error(apiErrorMessage(error, "加入购物车失败：后端服务暂不可用")); }
  };
  if (!product) return <main className="loading">{holder}{loadError
    ? <div role="alert"><p>{loadError}</p><Button onClick={() => { setLoadError(""); setAttempt((value) => value + 1); }}>重新加载</Button><p><a href="/">返回首页</a></p></div>
    : <Spin aria-label="正在加载商品详情" />}</main>;
  const referenceImage = productReferenceImage(product);
  return <main className="detail-page">{holder}<a href="/#collection" className="back-home"><ArrowLeft size={16} /> 返回系列</a>
    <div className="detail-grid"><div className="detail-images">
      <div className="detail-main"><img src={productImage(product)} alt={`${product.name} 项链展示`} width={640} height={420} /></div>
      {referenceImage ? <div className="detail-secondary"><img src={referenceImage} alt="血清素项链参考图" width={320} height={170} /></div> : <div className="image-placeholder">产品实拍图<br />待补充</div>}
      <div className="image-placeholder">模特佩戴图<br />待补充</div>
    </div><div className="detail-copy"><p className="eyebrow">MOLECULE PIECE / {String(product.id).padStart(2, "0")}</p><h1>{product.name}</h1>{product.tagline && <h2>{product.tagline}</h2>}<p className="detail-story">{product.story}</p><Tag color="gold">化学结构艺术饰品</Tag><Divider /><div className="price-row"><span>作品价格</span><strong>¥ {product.price}</strong></div><div className="detail-actions"><p className={product.stock ? "in-stock" : "sold-out"}>{product.stock ? <>{`余 ${product.stock} 件，可加入购物车`}{product.lowStock && <span className="low-stock">仅剩 {product.stock} 件</span>}</> : "暂时售罄"}</p><div className="detail-add-row"><Button size="large" type="primary" icon={<ShoppingBag size={17} />} disabled={!product.stock} onClick={add}>加入购物车</Button><span className="add-quantity"><span>数量</span><InputNumber min={1} max={product.stock} value={quantity} disabled={!product.stock} onChange={(value) => setQuantity(typeof value === "number" ? value : 1)} /></span></div><div className="detail-navigation"><Button size="large" onClick={() => { window.location.href = "/cart"; }}>查看购物车</Button><Button size="large" icon={<Home size={17} />} onClick={() => { window.location.href = "/"; }}>返回首页</Button></div></div><p className="detail-note">本作品只将化学结构转译为首饰语言，不涉及任何物质的获取或使用。</p></div></div><MoleculeCard productName={product.name} /><ProductComments productId={product.id} />
  </main>;
}
