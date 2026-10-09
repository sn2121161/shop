"use client";
import axios from "axios";
import { create } from "zustand";

export type Product = { id:number; name:string; price:number; tagline:string; story:string; image:string; stock:number; lowStock?:boolean };
const apiBaseUrl = (process.env.NEXT_PUBLIC_API_URL || "/api").replace(/\/api\/?$/, "");
const productAssetUrl = (path: string) => path.startsWith("/uploads/") ? `${apiBaseUrl}${path}` : path;
export const productImage = (product: Pick<Product, "name" | "image">) =>
  product.name === "血清素" ? "/images/serotonin-necklace.png" : product.name === "可卡因" ? "/images/cocaine-necklace.png" : productAssetUrl(product.image);
export const productReferenceImage = (product: Pick<Product, "name">) =>
  product.name === "血清素" ? "/images/serotonin-reference.jpg" : null;
export type CartItem = { id:number; product:Product; quantity:number; stock:number };
export const api = axios.create({
  baseURL: process.env.NEXT_PUBLIC_API_URL || "/api",
});
api.interceptors.request.use((config) => { const token = localStorage.getItem("mystery_token"); if (token) config.headers.Authorization = `Bearer ${token}`; return config; });
api.interceptors.response.use((response) => response, (error) => { if (axios.isAxiosError(error) && error.response?.status === 403 && error.response.data?.message === "该用户已停用") { localStorage.removeItem("mystery_token"); localStorage.removeItem("mystery_username"); localStorage.removeItem("mystery_role"); if (window.location.pathname !== "/login") window.location.href = "/login?reason=disabled"; } return Promise.reject(error); });
export const apiErrorMessage = (error: unknown, fallback: string) =>
  axios.isAxiosError<{ message?: string }>(error) ? error.response?.data?.message || fallback : fallback;
type ShopState = { token:string|null; username:string|null; role:string|null; cartCount:number; hydrate:()=>Promise<void>; setSession:(token:string, username:string, role:string)=>void; clearSession:()=>void; refreshCart:()=>Promise<void> };
// Keep the initial server and browser render identical. Browser-only session
// state is restored explicitly after React has hydrated the page.
export const useShop = create<ShopState>((set) => ({ token: null, username: null, role: null, cartCount: 0,
  hydrate: async () => { const token = localStorage.getItem("mystery_token"); const username = localStorage.getItem("mystery_username"); const role = localStorage.getItem("mystery_role"); set({ token, username, role }); if (token && (!username || !role)) { try { const { data } = await api.get<{username:string;role:string}>("/auth/me"); localStorage.setItem("mystery_username", data.username); localStorage.setItem("mystery_role", data.role); set({ username: data.username, role: data.role }); } catch { /* The regular auth flow will handle an expired token. */ } } },
  setSession: (token, username, role) => { localStorage.setItem("mystery_token", token); localStorage.setItem("mystery_username", username); localStorage.setItem("mystery_role", role); set({ token, username, role }); },
  clearSession: () => { localStorage.removeItem("mystery_token"); localStorage.removeItem("mystery_username"); localStorage.removeItem("mystery_role"); set({ token:null, username:null, role:null, cartCount:0 }); },
  refreshCart: async () => { try { const {data} = await api.get<CartItem[]>("/cart"); set({cartCount:data.reduce((total, item) => total + item.quantity, 0)}); } catch { set({cartCount:0}); } },
}));
