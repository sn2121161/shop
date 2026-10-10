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
const productAssetUrl = (path: string) => path.startsWith("/uploads/") ? `${apiBaseUrl}${path}` : path;
export const productImage = (product: Pick<Product, "name" | "image">) =>
  product.name === "血清素" ? "/images/serotonin-necklace.png" : product.name === "可卡因" ? "/images/cocaine-necklace.png" : productAssetUrl(product.image);
export const productReferenceImage = (product: Pick<Product, "name">) =>
  product.name === "血清素" ? "/images/serotonin-reference.jpg" : null;
export type CartItem = { id:number; product:Product; quantity:number; stock:number };
export const api = axios.create({
  baseURL: process.env.NEXT_PUBLIC_API_URL || "/api",
});
api.interceptors.request.use((config) => { const token = localStorage.getItem(sessionKey(currentScope(), "token")); if (token) config.headers.Authorization = `Bearer ${token}`; return config; });
api.interceptors.response.use((response) => response, (error) => { if (axios.isAxiosError(error) && error.response?.status === 403 && error.response.data?.message === "该用户已停用") { removeSession(currentScope()); if (window.location.pathname !== "/login") window.location.href = "/login?reason=disabled"; } return Promise.reject(error); });
export const apiErrorMessage = (error: unknown, fallback: string) =>
  axios.isAxiosError<{ message?: string }>(error) ? error.response?.data?.message || fallback : fallback;
type ShopState = { token:string|null; username:string|null; role:string|null; cartCount:number; hydrate:()=>Promise<void>; setSession:(token:string, username:string, role:string)=>void; clearSession:()=>void; refreshCart:()=>Promise<void> };
// Keep the initial server and browser render identical. Browser-only session
// state is restored explicitly after React has hydrated the page.
export const useShop = create<ShopState>((set) => ({ token: null, username: null, role: null, cartCount: 0,
  hydrate: async () => { const scope = currentScope(); const token = localStorage.getItem(sessionKey(scope, "token")); const username = localStorage.getItem(sessionKey(scope, "username")); const role = localStorage.getItem(sessionKey(scope, "role")); set({ token, username, role, cartCount: 0 }); if (token && (!username || !role)) { try { const { data } = await api.get<{username:string;role:string}>("/auth/me"); localStorage.setItem(sessionKey(scope, "username"), data.username); localStorage.setItem(sessionKey(scope, "role"), data.role); set({ username: data.username, role: data.role }); } catch { removeSession(scope); set({ token: null, username: null, role: null }); } } },
  setSession: (token, username, role) => { const scope: SessionScope = role === "admin" ? "admin" : "customer"; localStorage.setItem(sessionKey(scope, "token"), token); localStorage.setItem(sessionKey(scope, "username"), username); localStorage.setItem(sessionKey(scope, "role"), role); set({ token, username, role, cartCount: 0 }); },
  clearSession: () => { removeSession(currentScope()); set({ token:null, username:null, role:null, cartCount:0 }); },
  refreshCart: async () => { if (currentScope() === "admin") { set({ cartCount: 0 }); return; } try { const {data} = await api.get<CartItem[]>("/cart"); set({cartCount:data.reduce((total, item) => total + item.quantity, 0)}); } catch { set({cartCount:0}); } },
}));
