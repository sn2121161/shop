import assert from "node:assert/strict";
import { beforeEach, test } from "node:test";
import { AxiosError, type InternalAxiosRequestConfig } from "axios";
import { api, useShop } from "../app/shop";

let storage: Map<string, string>;
let redirects: string[];
let location: { pathname: string; href: string; assign: (url: string) => void };

function unauthorized(config: InternalAxiosRequestConfig, status = 401, message = "请先登录") {
  return new AxiosError("Request rejected", "ERR_BAD_REQUEST", config, undefined, {
    status, statusText: "Unauthorized", data: { message }, headers: {}, config,
  });
}

beforeEach(() => {
  storage = new Map(); redirects = [];
  location = { pathname: "/cart", get href() { return "http://localhost:3000" + this.pathname; },
    set href(value: string) { redirects.push(value); }, assign: (value) => redirects.push(value) };
  Object.defineProperty(globalThis, "window", { configurable: true, value: { location } });
  Object.defineProperty(globalThis, "localStorage", { configurable: true, value: {
    getItem: (key: string) => storage.get(key) ?? null,
    setItem: (key: string, value: string) => storage.set(key, value),
    removeItem: (key: string) => storage.delete(key),
  } });
  useShop.getState().setSession("expired-test-token", "demo", "customer");
  useShop.setState({ cartCount: 3 });
  api.defaults.adapter = async (config) => { throw unauthorized(config); };
});

test("401 clears stale identity and redirects to login", async () => {
  await assert.rejects(api.get("/cart"));
  assert.equal(storage.get("mystery_customer_token"), undefined);
  assert.deepEqual([useShop.getState().token, useShop.getState().username, useShop.getState().role, useShop.getState().cartCount], [null, null, null, 0]);
  assert.deepEqual(redirects, ["/login?reason=expired"]);
});

test("concurrent 401 responses cause only one redirect", async () => {
  await Promise.allSettled([api.get("/cart"), api.get("/account/address"), api.get("/payment-methods")]);
  assert.deepEqual(redirects, ["/login?reason=expired"]);
});

test("wrong login credentials do not trigger expiry navigation", async () => {
  location.pathname = "/login";
  await assert.rejects(api.post("/auth/login", { username: "demo", password: "incorrect" }));
  assert.deepEqual(redirects, []);
  assert.equal(storage.get("mystery_customer_token"), "expired-test-token");
});

test("already on login, a protected 401 clears identity without a loop", async () => {
  location.pathname = "/login";
  await assert.rejects(api.get("/auth/me"));
  assert.deepEqual(redirects, []);
  assert.equal(useShop.getState().token, null);
});

test("admin expiry preserves the customer session", async () => {
  location.pathname = "/admin";
  useShop.getState().setSession("expired-admin-token", "admin", "admin");
  await assert.rejects(api.get("/admin/dashboard"));
  assert.equal(storage.get("mystery_admin_token"), undefined);
  assert.equal(storage.get("mystery_customer_token"), "expired-test-token");
  assert.deepEqual(redirects, ["/login?reason=expired"]);
});

test("a delayed 401 cannot clear a newly authenticated session", async () => {
  let failRequest: () => void = () => { throw new Error("request did not start"); };
  api.defaults.adapter = (config) => new Promise((_, reject) => { failRequest = () => reject(unauthorized(config)); });
  const pending = api.get("/cart");
  await new Promise<void>((resolve) => setImmediate(resolve));
  useShop.getState().setSession("new-valid-token", "demo", "customer");
  failRequest(); await assert.rejects(pending);
  assert.equal(useShop.getState().token, "new-valid-token");
  assert.equal(storage.get("mystery_customer_token"), "new-valid-token");
  assert.deepEqual(redirects, []);
});

test("hydration checks a stored token even when profile fields are cached", async () => {
  await useShop.getState().hydrate();
  assert.equal(useShop.getState().token, null);
  assert.deepEqual(redirects, ["/login?reason=expired"]);
});

test("network errors do not clear a valid cached login", async () => {
  api.defaults.adapter = async (config) => { throw new AxiosError("Offline", "ERR_NETWORK", config); };
  await useShop.getState().hydrate();
  assert.equal(useShop.getState().token, "expired-test-token");
  assert.deepEqual(redirects, []);
});

test("disabled accounts still redirect and clear visible session state", async () => {
  api.defaults.adapter = async (config) => { throw unauthorized(config, 403, "该用户已停用"); };
  await assert.rejects(api.get("/cart"));
  assert.equal(useShop.getState().token, null);
  assert.deepEqual(redirects, ["/login?reason=disabled"]);
});
