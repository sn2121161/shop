"use client";

/* eslint-disable @next/next/no-html-link-for-pages -- Native document navigation avoids the current Vinext Link RSC runtime error. */

import { useEffect, useState, type FormEvent } from "react";
import { ArrowLeft, PackageSearch } from "lucide-react";
import { api, apiErrorMessage, useShop } from "../shop";

type Courier = { code: string; name: string; supported: boolean };
type Options = { enabled: boolean; provider: string; couriers: Courier[] };
type TrackingResult = { courierName: string; waybill: string; status: string; provider: string; queriedAt: string; subscriptionStatus?: string; latestEventAt?: string; updatedAt?: string; lastPushAt?: string; cached: boolean; traces: { time: string; description: string }[] };

function formatTime(value: string) {
  const date = new Date(value.includes("T") ? value : value.replace(" ", "T") + "+08:00");
  return Number.isNaN(date.getTime()) ? value : date.toLocaleString("zh-CN", { timeZone: "Asia/Shanghai", hour12: false });
}

export default function TrackingPage() {
  const [pushEnabled, setPushEnabled] = useState(false);
  const [options, setOptions] = useState<Options>();
  const [courier, setCourier] = useState("");
  const [waybill, setWaybill] = useState("");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");
  const [result, setResult] = useState<TrackingResult>();
  const { token, hydrate } = useShop();
  const normalized = waybill.replace(/\s/g, "").toUpperCase();
  const valid = (pushEnabled ? /^[A-Z0-9]{6,30}$/ : /^[A-Z0-9]{6,40}$/).test(normalized);
  const selected = options?.couriers.find((item) => item.code === courier);

  useEffect(() => { void hydrate(); }, [hydrate]);
  useEffect(() => {
    let cancelled = false;
    Promise.all([api.get<Options>("/tracking/options"), api.get<{ enabled: boolean }>("/tracking/subscription-options")]).then(([{ data }, subscription]) => {
      if (cancelled) return;
      setPushEnabled(subscription.data.enabled);
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
    <header><p className="eyebrow"><PackageSearch size={16} /> DELIVERY NOTES</p><h1>快递查询</h1><p>{pushEnabled ? "登记运单后，物流变化会自动同步到本站。" : "按快递公司查询，在这里查看包裹的物流轨迹。"}</p></header>
    <form className="tracking-panel" aria-label="按快递公司查询" onSubmit={query}>
      {!options && !error && <p role="status">正在加载查询配置…</p>}
      {options && !options.enabled && <p className="tracking-service-notice" role="status">站内物流查询尚未开通，需管理员配置快递鸟用户 ID 和 API Key。</p>}
      <fieldset className="courier-options" disabled={loading}><legend>选择快递公司</legend>
        <div>{options?.couriers.map((item) => <label key={item.code} className={courier === item.code ? "courier-option selected" : "courier-option"}>
          <input type="radio" name="courier" value={item.code} checked={courier === item.code} onChange={() => { setCourier(item.code); resetResult(); }} /><span>{item.name}<small>{item.supported ? "已接入" : "暂未接入"}</small></span>
        </label>)}</div>
      </fieldset>
      {selected && !selected.supported && <p className="tracking-service-notice">当前版本暂未接入{selected.name}，请选择圆通、申通、极兔或百世。</p>}
      <div className="waybill-field"><label htmlFor="tracking-waybill">{selected?.name || "快递"}运单号</label>
        <input id="tracking-waybill" value={waybill} onChange={(event) => { setWaybill(event.target.value); resetResult(); }} placeholder="请输入快递运单号" maxLength={pushEnabled ? 30 : 60} autoComplete="off" spellCheck={false} disabled={loading} aria-describedby="waybill-help" aria-invalid={Boolean(waybill.trim()) && !valid} />
        <p id="waybill-help">请输入 6–{pushEnabled ? 30 : 40} 位字母或数字，空格会自动忽略。商城订单号不能作为快递运单号。</p>
      </div>
      {token ? <button type="submit" className="tracking-submit" disabled={!valid || !options?.enabled || !selected?.supported || loading}>{loading ? "正在读取物流…" : pushEnabled ? "登记 / 查看最新物流" : "查询物流轨迹"}</button>
        : <a className="tracking-submit" href="/login">登录后查询物流</a>}
      <p className="tracking-external-note">{pushEnabled ? "首次登记会将单号提交至快递鸟，此后查看读取本站保存的物流推送。再次点击可刷新本站记录，不消耗主动查询次数。" : "查询由快递鸟提供，运单号会经本站后端发送给服务商。当前使用主动查询，结果短时缓存 5 分钟。"}</p>
      {error && <p className="tracking-query-error" role="alert">{error}</p>}
    </form>
    {result && <section className="tracking-result" aria-label="物流查询结果" aria-live="polite">
      <div className="tracking-result-heading"><div><p>{result.courierName} · {result.waybill}</p><h2>{result.status}</h2></div><span>来源：{result.provider}{result.subscriptionStatus ? " · 自动推送" : result.cached ? " · 5分钟内缓存" : ""}</span></div>
      {result.subscriptionStatus && <p role="status">{({ active: "已订阅，等待或接收快递鸟更新", pending: "订阅已登记，正在确认受理结果", uncertain: "订阅受理结果待确认，请联系管理员核对；系统不会重复提交", rejected: "订阅未获受理，请管理员核对订阅产品权限和请求要求" } as Record<string, string>)[result.subscriptionStatus]}</p>}
      <p className="tracking-result-time">快递更新于：{result.latestEventAt ? formatTime(result.latestEventAt) : result.traces[0]?.time || "等待首条物流轨迹"}</p>
      {result.updatedAt && <p className="tracking-result-time">本站同步于：{formatTime(result.updatedAt)}</p>}
      {result.lastPushAt && <p className="tracking-result-time">最近收到推送：{formatTime(result.lastPushAt)}</p>}
      {result.traces.length ? <ol className="tracking-timeline">{result.traces.map((trace, index) => <li key={`${trace.time}-${index}`}><time>{formatTime(trace.time)}</time><p>{trace.description}</p></li>)}</ol>
        : <p className="tracking-no-data">暂未查询到物流轨迹。请核对快递公司及运单号；新发出的包裹可能尚未被揽收。</p>}
      <p className="tracking-result-time">本次查看：{new Date(result.queriedAt).toLocaleString("zh-CN", { timeZone: "Asia/Shanghai" })}</p>
    </section>}
    <aside className="tracking-help"><h2>还没有运单号？</h2><p>请向商家获取发货后的实际运单号。当前商城订单不会自动生成运单；线下自提无需查询快递。</p><a href="https://www.kdniao.com/api-trackexpress" target="_blank" rel="noopener noreferrer">查看查询服务说明</a></aside>
  </main>;
}
