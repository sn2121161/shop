"use client";
import axios from "axios";
import { create } from "zustand";

export type Product = { id:number; name:string; price:number; tagline:string; story:string; image:string; stock:number; lowStock?:boolean };
const apiBaseUrl = (process.env.NEXT_PUBLIC_API_URL || "/api").replace(/\/api\/?$/, "");
type SessionScope = "admin" | "customer";
type SessionField = "token" | "username" | "role";
const currentScope = (): SessionScope => window.location.pathname.startsWith("/admin") ? "admin" : "customer";
const sessionKey = (scope: SessionScope, field: SessionField) => `mystery_${scope}_${field}`;
const removeSession = (scope: SessionScope) => (["token", "username", "role"] as SessionField[]).forEach((field) => localStorage.removeItem(sessionKey(scope, field)));
const requestSessions = new WeakMap<object, { scope: SessionScope; token: string | null }>();
let loginRedirectPending = false;

function invalidateSession(scope: SessionScope, reason: "expired" | "disabled") {
  removeSession(scope);
  // A response from a page we have left must not log out the other account scope.
  if (scope !== currentScope()) return;
  useShop.setState({ token: null, username: null, role: null, cartCount: 0 });
  if (window.location.pathname !== "/login" && !loginRedirectPending) {
    loginRedirectPending = true;
    window.location.assign(`/login?reason=${reason}`);
  }
}
const productAssetUrl = (path: string) => path.startsWith("/uploads/") ? `${apiBaseUrl}${path}` : path;
const productImages: Record<string, string> = {
  "血清素": "/images/serotonin-necklace.png",
  "可卡因": "/images/cocaine-necklace.png",
  "尼古丁": "/images/nicotine-necklace.png",
  "肾上腺素": "/images/adrenaline-necklace.png",
  "咖啡因": "/images/caffeine-necklace.png",
  "LSD": "/images/lsd-necklace.png",
  "苯": "/images/benzene-necklace.png",
  "吗啡": "/images/morphine-necklace.png",
  "地巴唑": "/images/bendazol-necklace.png",
  "戊巴比妥": "/images/pentobarbital-necklace.png",
  "薄荷醇": "/images/menthol-necklace.png",
  "乙醇": "/images/ethanol-necklace.png",
  "THC": "/images/thc-necklace.png",
  "迷幻剂": "/images/psychedelic-necklace.png",
  "海洛因I型": "/images/heroin-i-necklace.png",
  "海洛因II型": "/images/heroin-ii-necklace.png",
  "裸盖菇素": "/images/psilocybin-necklace.png",
};
export const productImage = (product: Pick<Product, "name" | "image">) =>
  productImages[product.name] ?? productAssetUrl(product.image);
export const productReferenceImage = (product: Pick<Product, "name">) =>
  product.name === "血清素" ? "/images/serotonin-reference.jpg" : null;
export type CartItem = { id:number; product:Product; quantity:number; stock:number };
export const api = axios.create({
  baseURL: process.env.NEXT_PUBLIC_API_URL || "/api",
});
api.interceptors.request.use((config) => {
  const scope = currentScope();
  const token = localStorage.getItem(sessionKey(scope, "token"));
  requestSessions.set(config, { scope, token });
  if (token) config.headers.Authorization = `Bearer ${token}`;
  return config;
});
api.interceptors.response.use((response) => response, (error) => {
  if (axios.isAxiosError(error)) {
    const request = error.config ? requestSessions.get(error.config) : undefined;
    const scope = request?.scope || currentScope();
    const sameSession = !request || request.token === localStorage.getItem(sessionKey(scope, "token"));
    const loginRequest = error.config?.url?.split("?")[0].replace(/\/+$/, "").endsWith("/auth/login");
    if (sameSession && error.response?.status === 401 && !loginRequest) invalidateSession(scope, "expired");
    if (sameSession && error.response?.status === 403 && error.response.data?.message === "该用户已停用") invalidateSession(scope, "disabled");
  }
  return Promise.reject(error);
});
export const apiErrorMessage = (error: unknown, fallback: string) =>
  axios.isAxiosError<{ message?: string }>(error) ? error.response?.data?.message || fallback : fallback;
type ShopState = { token:string|null; username:string|null; role:string|null; cartCount:number; hydrate:()=>Promise<void>; setSession:(token:string, username:string, role:string)=>void; clearSession:()=>void; refreshCart:()=>Promise<void> };
// Keep the initial server and browser render identical. Browser-only session
// state is restored explicitly after React has hydrated the page.
export const useShop = create<ShopState>((set) => ({ token: null, username: null, role: null, cartCount: 0,
  hydrate: async () => {
    const scope = currentScope();
    const token = localStorage.getItem(sessionKey(scope, "token"));
    const username = localStorage.getItem(sessionKey(scope, "username"));
    const role = localStorage.getItem(sessionKey(scope, "role"));
    set({ token, username, role, cartCount: 0 });
    if (!token) return;
    try {
      const { data } = await api.get<{username:string;role:string}>("/auth/me");
      if (localStorage.getItem(sessionKey(scope, "token")) !== token) return;
      localStorage.setItem(sessionKey(scope, "username"), data.username);
      localStorage.setItem(sessionKey(scope, "role"), data.role);
      if (scope === currentScope()) set({ username: data.username, role: data.role });
    } catch {
      // The response interceptor clears invalid sessions. Network failures alone
      // must not erase a stored login or a newer session established meanwhile.
    }
  },
  setSession: (token, username, role) => { loginRedirectPending = false; const scope: SessionScope = role === "admin" ? "admin" : "customer"; localStorage.setItem(sessionKey(scope, "token"), token); localStorage.setItem(sessionKey(scope, "username"), username); localStorage.setItem(sessionKey(scope, "role"), role); set({ token, username, role, cartCount: 0 }); },
  clearSession: () => { removeSession(currentScope()); set({ token:null, username:null, role:null, cartCount:0 }); },
  refreshCart: async () => { if (currentScope() === "admin") { set({ cartCount: 0 }); return; } try { const {data} = await api.get<CartItem[]>("/cart"); set({cartCount:data.reduce((total, item) => total + item.quantity, 0)}); } catch { set({cartCount:0}); } },
}));
