/*
 * The cabinet's service worker: the app shell offline, and nothing else.
 *
 * - Installing keeps the offline page (/offline, in the interface language
 *   and theme of that moment), the files it needs and the app icons.
 * - Pages always come from the network; without a connection the offline
 *   page answers instead. Pages are never stored: they hold personal data.
 * - The cabinet's own build files (/_next/static/, named by their content,
 *   so they never change) are kept once loaded and served from the cache.
 * - API calls (/api/*) and everything from other sites pass straight
 *   through: no API data is ever cached.
 * - A push message {title, body, url, tag} shows a notification; pressing
 *   it opens the url (a page of the cabinet) in a cabinet window.
 * - The page posts {type: "refresh-offline-page"} after a change of
 *   language or theme, so the offline page follows it.
 *
 * Registered by src/components/shell/ServiceWorker.tsx. Tests:
 * src/lib/serviceWorker.test.ts runs this file against fakes.
 */

const VERSION = "aw-1";
const SHELL_CACHE = `${VERSION}-shell`;
const STATIC_CACHE = `${VERSION}-static`;
const OFFLINE_PATH = "/offline";
const ICONS = ["/icons/icon-192.png", "/icons/icon-512.png", "/icons/maskable-192.png", "/icons/maskable-512.png"];
const STATIC_PREFIX = "/_next/static/";
const ASSET_PATTERN = /\/_next\/static\/[^"'\s)<>\\]+/g;

/** The /_next/static/ files a page's HTML loads (scripts, styles, fonts). */
function assetsOf(html) {
  return [...new Set(html.match(ASSET_PATTERN) ?? [])].map((path) => path.replace(/&amp;/g, "&"));
}

/** Stores the offline page as it renders now and the build files it needs. */
async function keepOfflinePage() {
  const response = await fetch(OFFLINE_PATH, { credentials: "same-origin", cache: "no-store" });
  if (!response.ok) {
    return;
  }
  const shell = await caches.open(SHELL_CACHE);
  await shell.put(OFFLINE_PATH, response.clone());
  const assets = assetsOf(await response.text());
  const statics = await caches.open(STATIC_CACHE);
  await Promise.all(
    assets.map(async (path) => {
      if (!(await statics.match(path))) {
        await statics.add(path).catch(() => undefined);
      }
    }),
  );
}

async function install() {
  const shell = await caches.open(SHELL_CACHE);
  await shell.addAll(ICONS);
  await keepOfflinePage();
  await self.skipWaiting();
}

/** Drops the caches of earlier versions and takes over the open pages. */
async function activate() {
  const names = await caches.keys();
  await Promise.all(names.filter((name) => name !== SHELL_CACHE && name !== STATIC_CACHE).map((name) => caches.delete(name)));
  await self.clients.claim();
}

async function offlineAnswer() {
  const cached = await caches.match(OFFLINE_PATH, { cacheName: SHELL_CACHE });
  return cached ?? new Response("Offline", { status: 503, headers: { "content-type": "text/plain; charset=utf-8" } });
}

async function fromNetworkOrOffline(request) {
  try {
    return await fetch(request);
  } catch {
    return offlineAnswer();
  }
}

async function fromCacheOrNetwork(request, cacheName) {
  const cache = await caches.open(cacheName);
  const cached = await cache.match(request);
  if (cached) {
    return cached;
  }
  const response = await fetch(request);
  if (response.ok) {
    await cache.put(request, response.clone());
  }
  return response;
}

/** How a request is answered: "page", "static", "icon" or null (left to the browser). */
function routeOf(request) {
  if (request.method !== "GET") {
    return null;
  }
  const url = new URL(request.url);
  if (url.origin !== self.location.origin || url.pathname.startsWith("/api/")) {
    return null;
  }
  if (request.mode === "navigate") {
    return "page";
  }
  if (url.pathname.startsWith(STATIC_PREFIX)) {
    return "static";
  }
  return ICONS.includes(url.pathname) ? "icon" : null;
}

function onFetch(event) {
  const route = routeOf(event.request);
  if (route === "page") {
    event.respondWith(fromNetworkOrOffline(event.request));
  } else if (route === "static") {
    event.respondWith(fromCacheOrNetwork(event.request, STATIC_CACHE));
  } else if (route === "icon") {
    event.respondWith(fromCacheOrNetwork(event.request, SHELL_CACHE));
  }
}

/** A same-site page to open, or the businesses for anything else. */
function safeTarget(url) {
  try {
    const target = new URL(typeof url === "string" ? url : "/businesses", self.location.origin);
    return target.origin === self.location.origin ? target.href : new URL("/businesses", self.location.origin).href;
  } catch {
    return new URL("/businesses", self.location.origin).href;
  }
}

function onPush(event) {
  let message = {};
  try {
    message = event.data ? event.data.json() : {};
  } catch {
    message = { body: event.data ? event.data.text() : "" };
  }
  const title = typeof message.title === "string" && message.title ? message.title : "Assistant Workshop";
  event.waitUntil(
    self.registration.showNotification(title, {
      body: typeof message.body === "string" ? message.body : "",
      tag: typeof message.tag === "string" ? message.tag : undefined,
      icon: "/icons/icon-192.png",
      badge: "/icons/maskable-192.png",
      data: { url: safeTarget(message.url) },
    }),
  );
}

async function openTarget(url) {
  const windows = await self.clients.matchAll({ type: "window", includeUncontrolled: true });
  const open = windows.find((client) => client.url === url);
  if (open) {
    return open.focus();
  }
  return self.clients.openWindow(url);
}

function onNotificationClick(event) {
  event.notification.close();
  event.waitUntil(openTarget(safeTarget(event.notification.data && event.notification.data.url)));
}

function onMessage(event) {
  if (event.data && event.data.type === "refresh-offline-page") {
    event.waitUntil(keepOfflinePage());
  }
}

self.addEventListener("install", (event) => event.waitUntil(install()));
self.addEventListener("activate", (event) => event.waitUntil(activate()));
self.addEventListener("fetch", onFetch);
self.addEventListener("push", onPush);
self.addEventListener("notificationclick", onNotificationClick);
self.addEventListener("message", onMessage);
