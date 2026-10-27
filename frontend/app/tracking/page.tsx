"use client";

/* eslint-disable @next/next/no-html-link-for-pages -- Native document navigation avoids the current Vinext Link RSC runtime error. */

import { useEffect, useState, type FormEvent } from "react";
import { ArrowLeft, PackageSearch } from "lucide-react";
import { api, apiErrorMessage, useShop } from "../shop";

type Courier = { code: string; name: string; supported: boolean };
type Options = { enabled: boolean; provider: string; couriers: Courier[] };
type TrackingResult = { courierName: string; waybill: string; status: string; provider: string; queriedAt: string; cached: boolean; traces: { time: string; description: string }[] };

export default function TrackingPage() {
  const [options, setOptions] = useState<Options>();
  const [courier, setCourier] = useState("");
  const [waybill, setWaybill] = useState("");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");
  const [result, setResult] = useState<TrackingResult>();
  const { token, hydrate } = useShop();
  const normalized = waybill.replace(/\s/g, "").toUpperCase();
  const valid = /^[A-Z0-9]{6,40}$/.test(normalized);
  const selected = options?.couriers.find((item) => item.code === courier);

  useEffect(() => { void hydrate(); }, [hydrate]);
  useEffect(() => {
    let cancelled = false;
    api.get<Options>("/tracking/options").then(({ data }) => {
      if (cancelled) return;
      setOptions(data); setCourier(data.couriers.find((item) => item.supported)?.code || "");
    }).catch(() => { if (!cancelled) setError("查询配置暂时无法加载，请刷新页面重试"); });
    return () => { cancelled = true; };
  }, []);

  const query = async (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    if (!valid || !token || !options?.enabled || !selected?.supported || loading) return;
    setLoading(true); setResult(undefined); setError("");
    try { const { data } = await api.post<TrackingResult>("/tracking/query", { courier, waybill: normalized }); setResult(data); }
    catch (failure: unknown) { setError(apiErrorMessage(failure, "物流查询失败，请稍后重试")); }
    finally { setLoading(false); }
  };
  const resetResult = () => { setResult(undefined); setError(""); };

  return <main className="tracking-page">
    <a href="/" className="back-home"><ArrowLeft size={16} /> 返回小屋</a>
    <header><p className="eyebrow"><PackageSearch size={16} /> DELIVERY NOTES</p><h1>快递查询</h1><p>按快递公司查询，在这里查看包裹的物流轨迹。</p></header>
    <form className="tracking-panel" aria-label="按快递公司查询" onSubmit={query}>
      {!options && !error && <p role="status">正在加载查询配置…</p>}
      {options && !options.enabled && <p className="tracking-service-notice" role="status">站内物流查询尚未开通，需管理员配置快递鸟用户 ID 和 API Key。</p>}
      <fieldset className="courier-options" disabled={loading}><legend>选择快递公司</legend>
        <div>{options?.couriers.map((item) => <label key={item.code} className={courier === item.code ? "courier-option selected" : "courier-option"}>
          <input type="radio" name="courier" value={item.code} checked={courier === item.code} onChange={() => { setCourier(item.code); resetResult(); }} /><span>{item.name}<small>{item.supported ? "免费方案支持" : "免费方案未覆盖"}</small></span>
        </label>)}</div>
      </fieldset>
      {selected && !selected.supported && <p className="tracking-service-notice">当前免费方案未覆盖{selected.name}。请选择圆通、申通、极兔或百世；本站不会自动切换到付费接口。</p>}
      <div className="waybill-field"><label htmlFor="tracking-waybill">{selected?.name || "快递"}运单号</label>
        <input id="tracking-waybill" value={waybill} onChange={(event) => { setWaybill(event.target.value); resetResult(); }} placeholder="请输入快递运单号" maxLength={60} autoComplete="off" spellCheck={false} disabled={loading} aria-describedby="waybill-help" aria-invalid={Boolean(waybill.trim()) && !valid} />
        <p id="waybill-help">请输入 6–40 位字母或数字，空格会自动忽略。商城订单号不能作为快递运单号。</p>
      </div>
      {token ? <button type="submit" className="tracking-submit" disabled={!valid || !options?.enabled || !selected?.supported || loading}>{loading ? "正在查询物流…" : "查询物流轨迹"}</button>
        : <a className="tracking-submit" href="/login">登录后查询物流</a>}
      <p className="tracking-external-note">查询由快递鸟提供，运单号会经本站后端发送给服务商。结果仅短时缓存 5 分钟，不写入数据库；物流轨迹以快递公司返回为准。</p>
      {error && <p className="tracking-query-error" role="alert">{error}</p>}
    </form>
    {result && <section className="tracking-result" aria-label="物流查询结果" aria-live="polite">
      <div className="tracking-result-heading"><div><p>{result.courierName} · {result.waybill}</p><h2>{result.status}</h2></div><span>来源：{result.provider}{result.cached ? " · 5分钟内缓存" : ""}</span></div>
      {result.traces.length ? <ol className="tracking-timeline">{result.traces.map((trace, index) => <li key={`${trace.time}-${index}`}><time>{trace.time}</time><p>{trace.description}</p></li>)}</ol>
        : <p className="tracking-no-data">暂未查询到物流轨迹。请核对快递公司及运单号；新发出的包裹可能尚未被揽收。</p>}
      <p className="tracking-result-time">查询时间：{new Date(result.queriedAt).toLocaleString("zh-CN", { timeZone: "Asia/Shanghai" })}</p>
    </section>}
    <aside className="tracking-help"><h2>还没有运单号？</h2><p>请向商家获取发货后的实际运单号。当前商城订单不会自动生成运单；线下自提无需查询快递。</p><a href="https://www.kdniao.com/product-track2" target="_blank" rel="noopener noreferrer">查看免费方案说明</a></aside>
  </main>;
}
