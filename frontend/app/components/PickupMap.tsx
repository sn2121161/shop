"use client";

import { useEffect, useRef, useState } from "react";
import { Button, message } from "antd";
import { Copy, ExternalLink, MapPin } from "lucide-react";

const storeName = "小行星桌游社";
const storeAddress = "常州市天宁区文化广场小行星桌游社";
// AMap POI B0K6LDM3P4: 小行星桌游社·日麻·跑团, 文化广场地下一层69号铺.
// Coordinates returned by AMap PlaceSearch (GCJ-02), not the old OSM landmark.
const storePosition: [number, number] = [119.972747, 31.806285];
const searchUrl = `https://uri.amap.com/search?${new URLSearchParams({
  keyword: storeAddress, city: "常州", view: "map", src: "molecule-shop", callnative: "1",
})}`;
const mapKey = process.env.NEXT_PUBLIC_AMAP_KEY;
const securityCode = process.env.NEXT_PUBLIC_AMAP_SECURITY_JS_CODE;
const configured = Boolean(mapKey && securityCode);

type MapInstance = {
  destroy(): void;
  addControl(control: object): void;
  on(event: string, callback: () => void): void;
};
type MapSdk = {
  Map: new (container: HTMLElement, options: object) => MapInstance;
  Scale: new () => object;
  ToolBar: new () => object;
  Marker: new (options: object) => object;
};
type AmapWindow = Window & {
  _AMapSecurityConfig?: { securityJsCode: string };
  AMapLoader?: { load(options: object): Promise<MapSdk> };
};
let sdkPromise: Promise<MapSdk> | undefined;

function loadMap(): Promise<MapSdk> {
  if (sdkPromise) return sdkPromise;
  const target = window as AmapWindow;
  target._AMapSecurityConfig = { securityJsCode: securityCode! };
  sdkPromise = new Promise<MapSdk>((resolve, reject) => {
    const script = document.createElement("script");
    const timeout = window.setTimeout(() => fail(), 15000);
    function fail() {
      window.clearTimeout(timeout);
      script.remove();
      reject(new Error("地图加载失败"));
    }
    script.src = "https://webapi.amap.com/loader.js";
    script.async = true;
    script.onerror = fail;
    script.onload = () => {
      if (!target.AMapLoader) { fail(); return; }
      target.AMapLoader.load({
        key: mapKey, version: "2.0", plugins: ["AMap.Scale", "AMap.ToolBar"],
      }).then((sdk) => { window.clearTimeout(timeout); resolve(sdk); }, fail);
    };
    document.head.appendChild(script);
  }).catch((error: unknown) => { sdkPromise = undefined; throw error; });
  return sdkPromise;
}

export default function PickupMap() {
  const container = useRef<HTMLDivElement>(null);
  const [attempt, setAttempt] = useState(0);
  const [state, setState] = useState<"loading" | "ready" | "error">("loading");
  const [notice, holder] = message.useMessage();

  useEffect(() => {
    if (!configured) return;
    let cancelled = false;
    let map: MapInstance | undefined;
    const timeout = window.setTimeout(() => {
      if (!cancelled) { cancelled = true; map?.destroy(); map = undefined; setState("error"); }
    }, 20000);
    loadMap().then((sdk) => {
      if (cancelled || !container.current) return;
      map = new sdk.Map(container.current, {
        center: storePosition, zoom: 17, viewMode: "2D", resizeEnable: true,
      });
      map.addControl(new sdk.Scale());
      map.addControl(new sdk.ToolBar());
      map.on("complete", () => {
        if (!cancelled) { window.clearTimeout(timeout); setState("ready"); }
      });
      new sdk.Marker({
        map, position: storePosition, title: storeName, anchor: "center", zIndex: 200,
        content: '<div class="pickup-store-marker" role="img" aria-label="小行星桌游社位置"><span class="pickup-store-dot"></span><span class="pickup-store-label">小行星桌游社</span></div>',
      });
    }).catch(() => {
      if (!cancelled) {
        cancelled = true;
        window.clearTimeout(timeout);
        map?.destroy();
        map = undefined;
        setState("error");
      }
    });
    return () => {
      cancelled = true;
      window.clearTimeout(timeout);
      map?.destroy();
    };
  }, [attempt]);

  const copyAddress = async () => {
    try { await navigator.clipboard.writeText(storeAddress); notice.success("自提地址已复制"); }
    catch { notice.info("请选中上方地址，手动复制"); }
  };
  const statusText = !configured ? "点击下方按钮，在高德地图中搜索自提点。"
    : state === "error" ? "地图暂时无法加载，仍可打开高德搜索或复制地址。"
    : state === "loading" ? "正在加载高德地图…"
    : "红点标记小行星桌游社 · 文化广场地下一层69号铺。";

  return <section className="pickup-location" aria-label="自提点地图">
    {holder}
    <div className="pickup-store"><b><MapPin size={16} aria-hidden="true" /> 自提点</b><span>{storeAddress}</span></div>
    <p className="pickup-contact-note">到店前请与商家确认具体门牌及营业时间。</p>
    {configured && <div className="pickup-map-shell" aria-busy={state === "loading"}>
      <div ref={container} className="pickup-amap" role="region" aria-label="高德自提点地图" />
      {state !== "ready" && <div className="pickup-map-placeholder"><MapPin size={30} aria-hidden="true" /><span>{state === "error" ? "地图暂不可用" : "正在加载地图"}</span></div>}
    </div>}
    <p className="pickup-map-status" role="status">{statusText}</p>
    <div className="pickup-map-actions">
      <Button type="primary" href={searchUrl} target="_blank" rel="noopener noreferrer" icon={<ExternalLink size={15} />}>高德搜索自提点</Button>
      <Button onClick={copyAddress} icon={<Copy size={15} />}>复制地址</Button>
      {configured && state === "error" && <Button onClick={() => { setState("loading"); setAttempt((value) => value + 1); }}>重新加载</Button>}
    </div>
  </section>;
}
