/**
 * public/sw.js, run against fakes of the service worker globals: what it
 * keeps on install, what it answers offline, what it never touches (API
 * calls, other sites, writes) and its push notifications.
 */

import { readFileSync } from "node:fs";
import path from "node:path";

import { beforeEach, describe, expect, it, vi } from "vitest";

const ORIGIN = "https://cabinet.example";
const SOURCE = readFileSync(path.join(__dirname, "../../public/sw.js"), "utf8");
const OFFLINE_HTML = `<html><link rel="stylesheet" href="/_next/static/css/app.css"><script src="/_next/static/chunks/main.js"></script><script>self.__next_f.push([1,"\\"/_next/static/chunks/page.js\\""])</script></html>`;

const keyOf = (request: Request | string) => {
  const url = new URL(typeof request === "string" ? request : request.url, ORIGIN);
  return `${url.pathname}${url.search}`;
};

class FakeCache {
  readonly entries = new Map<string, Response>();
  constructor(private readonly network: (request: Request | string) => Promise<Response>) {}
  async match(request: Request | string) {
    return this.entries.get(keyOf(request))?.clone();
  }
  async put(request: Request | string, response: Response) {
    this.entries.set(keyOf(request), response);
  }
  async add(request: string) {
    const response = await this.network(request);
    if (!response.ok) {
      throw new Error(`${request}: ${response.status}`);
    }
    await this.put(request, response);
  }
  async addAll(requests: string[]) {
    await Promise.all(requests.map((request) => this.add(request)));
  }
}

interface Handled {
  responded?: Promise<Response>;
  waited?: Promise<unknown>;
}

function startWorker(search = "") {
  const handlers = new Map<string, (event: unknown) => void>();
  let online = true;
  const network = vi.fn(async (request: Request | string) => {
    if (!online) {
      throw new TypeError("Failed to fetch");
    }
    const key = keyOf(request);
    if (key === "/offline") {
      return new Response(OFFLINE_HTML, { headers: { "content-type": "text/html" } });
    }
    return new Response(`body of ${key}`, { status: key.includes("missing") ? 404 : 200 });
  });
  const stores = new Map<string, FakeCache>();
  const caches = {
    open: async (name: string) => stores.get(name) ?? stores.set(name, new FakeCache(network)).get(name)!,
    keys: async () => [...stores.keys()],
    delete: async (name: string) => stores.delete(name),
    match: async (request: Request | string, options: { cacheName: string }) => stores.get(options.cacheName)?.match(request),
  };
  const windows = [{ url: `${ORIGIN}/b/biz/messages`, focus: vi.fn(async () => "focused") }];
  const self = {
    location: { origin: ORIGIN, search },
    addEventListener: (type: string, handler: (event: unknown) => void) => handlers.set(type, handler),
    skipWaiting: vi.fn(async () => undefined),
    clients: { claim: vi.fn(async () => undefined), matchAll: vi.fn(async () => windows), openWindow: vi.fn(async () => "opened") },
    registration: { showNotification: vi.fn(async () => undefined) },
  };
  new Function("self", "caches", "fetch", SOURCE)(self, caches, network);

  const dispatch = (type: string, event: Record<string, unknown> = {}): Handled => {
    const handled: Handled = {};
    handlers.get(type)?.({
      ...event,
      respondWith: (response: Promise<Response>) => (handled.responded = response),
      waitUntil: (promise: Promise<unknown>) => (handled.waited = promise),
    });
    return handled;
  };
  // `new Request` refuses mode "navigate" (only the browser makes those): set it afterwards.
  const request = (url: string, { mode = "cors", ...init }: Omit<RequestInit, "mode"> & { mode?: string } = {}) => {
    const value = new Request(new URL(url, ORIGIN), init);
    Object.defineProperty(value, "mode", { value: mode });
    return value;
  };
  return { self, stores, network, dispatch, request, windows, goOffline: () => (online = false) };
}

let worker: ReturnType<typeof startWorker>;

beforeEach(async () => {
  worker = startWorker();
  await worker.dispatch("install").waited;
});

describe("service worker: install and activate", () => {
  it("keeps the offline page, the files it loads and the icons", async () => {
    const shell = worker.stores.get("aw-1-shell")!;
    const statics = worker.stores.get("aw-1-static")!;
    expect([...shell.entries.keys()].sort()).toEqual([
      "/icons/icon-192.png",
      "/icons/icon-512.png",
      "/icons/maskable-192.png",
      "/icons/maskable-512.png",
      "/offline",
    ]);
    expect([...statics.entries.keys()].sort()).toEqual([
      "/_next/static/chunks/main.js",
      "/_next/static/chunks/page.js",
      "/_next/static/css/app.css",
    ]);
    expect(worker.self.skipWaiting).toHaveBeenCalled();
  });

  it("drops the caches of earlier versions and takes over open pages", async () => {
    await (await worker.stores.get("aw-1-shell"))!.put("/x", new Response("x"));
    worker.stores.set("aw-0-shell", new FakeCache(worker.network));
    await worker.dispatch("activate").waited;
    expect([...worker.stores.keys()].sort()).toEqual(["aw-1-shell", "aw-1-static"]);
    expect(worker.self.clients.claim).toHaveBeenCalled();
  });
});

describe("service worker: requests", () => {
  it("loads pages from the network and shows the offline page without one", async () => {
    const online = worker.dispatch("fetch", { request: worker.request("/b/biz/overview", { mode: "navigate" }) });
    expect(await (await online.responded!).text()).toBe("body of /b/biz/overview");

    worker.goOffline();
    const offline = worker.dispatch("fetch", { request: worker.request("/b/biz/messages", { mode: "navigate" }) });
    expect(await (await offline.responded!).text()).toBe(OFFLINE_HTML);
  });

  it("serves build files from the cache once loaded", async () => {
    const first = worker.dispatch("fetch", { request: worker.request("/_next/static/chunks/other.js") });
    expect(await (await first.responded!).text()).toBe("body of /_next/static/chunks/other.js");
    worker.goOffline();
    const again = worker.dispatch("fetch", { request: worker.request("/_next/static/chunks/other.js") });
    expect(await (await again.responded!).text()).toBe("body of /_next/static/chunks/other.js");
  });

  it("does not keep a build file the server did not find", async () => {
    const missing = worker.dispatch("fetch", { request: worker.request("/_next/static/missing.js") });
    expect((await missing.responded!).status).toBe(404);
    expect(worker.stores.get("aw-1-static")!.entries.has("/_next/static/missing.js")).toBe(false);
  });

  it("never touches API calls, other sites, writes or other files", () => {
    const untouched = [
      worker.request("/api/backend/v1/me"),
      worker.request("https://other.example/x.js"),
      worker.request("/api/auth/logout", { method: "POST", mode: "navigate" }),
      worker.request("/robots.txt"),
    ];
    for (const request of untouched) {
      expect(worker.dispatch("fetch", { request }).responded).toBeUndefined();
    }
  });

  it("keeps the offline page again when asked", async () => {
    worker.network.mockClear();
    await worker.dispatch("message", { origin: ORIGIN, data: { type: "refresh-offline-page" } }).waited;
    expect(worker.network).toHaveBeenCalledWith("/offline", expect.objectContaining({ cache: "no-store" }));
    expect(worker.dispatch("message", { origin: ORIGIN, data: { type: "other" } }).waited).toBeUndefined();
    expect(worker.dispatch("message", { origin: "https://elsewhere.example", data: { type: "refresh-offline-page" } }).waited).toBeUndefined();
  });
});

describe("service worker: notifications", () => {
  const push = (payload: unknown) => ({ data: { json: () => payload, text: () => String(payload) } });

  it("shows a pushed message with a link into the cabinet only", async () => {
    await worker.dispatch("push", push({ title: "New handoff", body: "Nino needs a person", url: "/b/biz/messages/c1", tag: "h1" })).waited;
    await worker.dispatch("push", push({ title: "", url: "https://evil.example/" })).waited;
    const calls = worker.self.registration.showNotification.mock.calls as unknown as [string, { data: { url: string }; tag?: string }][];
    expect(calls[0]?.[0]).toBe("New handoff");
    expect(calls[0]?.[1]).toMatchObject({ body: "Nino needs a person", tag: "h1", data: { url: `${ORIGIN}/b/biz/messages/c1` } });
    expect(calls[1]?.[0]).toBe("Assistant Workshop");
    expect(calls[1]?.[1].data.url).toBe(`${ORIGIN}/businesses`);
  });

  it("opens the message's page, or focuses the window already showing it", async () => {
    const notification = (url: string) => ({ notification: { close: vi.fn(), data: { url } } });
    await worker.dispatch("notificationclick", notification(`${ORIGIN}/b/biz/messages`)).waited;
    expect(worker.windows[0]?.focus).toHaveBeenCalled();
    await worker.dispatch("notificationclick", notification(`${ORIGIN}/b/biz/bookings`)).waited;
    expect(worker.self.clients.openWindow).toHaveBeenCalledWith(`${ORIGIN}/b/biz/bookings`);
  });
});

describe("service worker: push only (a development server)", () => {
  it("keeps nothing and leaves requests alone, but shows notifications", async () => {
    const pushOnly = startWorker("?push-only=1");
    await pushOnly.dispatch("install").waited;

    expect(pushOnly.stores.size).toBe(0);
    expect(pushOnly.self.skipWaiting).toHaveBeenCalled();
    const page = pushOnly.request("/b/biz/overview", { mode: "navigate" });
    expect(pushOnly.dispatch("fetch", { request: page }).responded).toBeUndefined();
    const chunk = pushOnly.request("/_next/static/chunks/main.js");
    expect(pushOnly.dispatch("fetch", { request: chunk }).responded).toBeUndefined();
    const message = { data: { json: () => ({ title: "Test", url: "/n/token" }), text: () => "" } };
    await pushOnly.dispatch("push", message).waited;
    expect(pushOnly.self.registration.showNotification).toHaveBeenCalledWith(
      "Test",
      expect.objectContaining({ data: { url: `${ORIGIN}/n/token` } }),
    );
  });
});
