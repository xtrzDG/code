/**
 * "Enable notifications on this device": the browser's Push API around the
 * cabinet's service worker (public/sw.js, which shows the notifications).
 *
 *  1. The browser asks the person to allow notifications for the site.
 *  2. The service worker subscribes at the browser's push service with the
 *     platform's public VAPID key (WEB_PUSH_VAPID_PUBLIC_KEY, given by the
 *     API); the subscription is an address at the push service and two keys.
 *  3. The cabinet sends the subscription to the API, which encrypts every
 *     notification for these keys (the push service never reads it).
 *
 * Which device in the API's list is this browser is remembered per business
 * in localStorage (the subscription's address and the device id).
 *
 * Production builds register the worker on every signed-in page
 * (components/shell/ServiceWorker.tsx). Elsewhere it is registered when a
 * device is turned on, as `/sw.js?push-only=1`, which only shows
 * notifications and leaves requests alone (no build files are cached
 * while the code changes).
 */

import type { RequestBody } from "@/api/types";

export type PushSubscriptionBody = RequestBody<"/v1/businesses/{business_id}/push-subscriptions", "post">;

export type PushSupport = "supported" | "unsupported" | "denied";

const DEVICE_KEY_PREFIX = "aw_push_device:";

/** What this browser can do: notify, not at all, or not since the person blocked the site. */
export function pushSupportOf(environment: {
  hasServiceWorker: boolean;
  hasPushManager: boolean;
  permission: NotificationPermission | null;
}): PushSupport {
  if (!environment.hasServiceWorker || !environment.hasPushManager || environment.permission === null) {
    return "unsupported";
  }
  return environment.permission === "denied" ? "denied" : "supported";
}

export function currentPushSupport(): PushSupport {
  if (typeof window === "undefined") {
    return "unsupported";
  }
  return pushSupportOf({
    hasServiceWorker: "serviceWorker" in navigator,
    hasPushManager: "PushManager" in window,
    permission: "Notification" in window ? Notification.permission : null,
  });
}

/** The VAPID public key (base64url) as the bytes `pushManager.subscribe` takes. */
export function applicationServerKey(publicKey: string): Uint8Array<ArrayBuffer> {
  const base64 = publicKey.replace(/-/g, "+").replace(/_/g, "/") + "=".repeat((4 - (publicKey.length % 4)) % 4);
  const binary = atob(base64);
  const bytes = new Uint8Array(new ArrayBuffer(binary.length));
  for (let index = 0; index < binary.length; index += 1) {
    bytes[index] = binary.charCodeAt(index);
  }
  return bytes;
}

/** The API body of a browser subscription, or null when the browser gave no keys. */
export function subscriptionBody(subscription: PushSubscriptionJSON, language: string): PushSubscriptionBody | null {
  const p256dh = subscription.keys?.p256dh;
  const auth = subscription.keys?.auth;
  if (!subscription.endpoint || !p256dh || !auth) {
    return null;
  }
  return { endpoint: subscription.endpoint, keys: { p256dh, auth }, language };
}

/** Whether a subscription was made with this key (another server key needs a new one). */
export function isSubscribedWithKey(subscription: PushSubscription, publicKey: string): boolean {
  const key = subscription.options?.applicationServerKey;
  if (!key) {
    return true;
  }
  const given = new Uint8Array(key);
  const expected = applicationServerKey(publicKey);
  return given.length === expected.length && given.every((byte, index) => byte === expected[index]);
}

export interface RememberedDevice {
  endpoint: string;
  deviceId: string;
}

/** The stored text of this browser's device in a business (a stable value for useSyncExternalStore). */
export function rememberedDeviceText(storage: Pick<Storage, "getItem"> | null, businessId: string): string | null {
  try {
    return storage?.getItem(DEVICE_KEY_PREFIX + businessId) ?? null;
  } catch {
    // Blocked storage: the device is simply not recognised.
    return null;
  }
}

export function parseRememberedDevice(raw: string | null): RememberedDevice | null {
  try {
    const parsed: unknown = raw ? JSON.parse(raw) : null;
    if (parsed && typeof parsed === "object" && "endpoint" in parsed && "deviceId" in parsed) {
      const { endpoint, deviceId } = parsed as Record<string, unknown>;
      if (typeof endpoint === "string" && typeof deviceId === "string") {
        return { endpoint, deviceId };
      }
    }
  } catch {
    // A broken entry: the device is simply not recognised.
  }
  return null;
}

export function readRememberedDevice(storage: Pick<Storage, "getItem"> | null, businessId: string): RememberedDevice | null {
  return parseRememberedDevice(rememberedDeviceText(storage, businessId));
}

export function rememberDevice(
  storage: Pick<Storage, "setItem" | "removeItem"> | null,
  businessId: string,
  device: RememberedDevice | null,
): void {
  try {
    if (device === null) {
      storage?.removeItem(DEVICE_KEY_PREFIX + businessId);
    } else {
      storage?.setItem(DEVICE_KEY_PREFIX + businessId, JSON.stringify(device));
    }
  } catch {
    // Nothing to remember it in: the device shows as off after a reload.
  }
  notifyPushState();
}

/** Whether another business of this browser still relies on its one push subscription. */
export function isEndpointRememberedElsewhere(storage: Storage | null, businessId: string, endpoint: string): boolean {
  if (storage === null) {
    return true;
  }
  try {
    for (let index = 0; index < storage.length; index += 1) {
      const key = storage.key(index);
      if (key?.startsWith(DEVICE_KEY_PREFIX) && key !== DEVICE_KEY_PREFIX + businessId) {
        if (parseRememberedDevice(storage.getItem(key))?.endpoint === endpoint) {
          return true;
        }
      }
    }
  } catch {
    return true;
  }
  return false;
}

const listeners = new Set<() => void>();

/** Tell the hooks that read the browser's push state (support, remembered devices) to read it again. */
export function notifyPushState(): void {
  listeners.forEach((listener) => listener());
}

export function subscribePushState(listener: () => void): () => void {
  listeners.add(listener);
  return () => {
    listeners.delete(listener);
  };
}

export function browserStorage(): Storage | null {
  try {
    return typeof window === "undefined" ? null : window.localStorage;
  } catch {
    return null;
  }
}

/** The worker that receives pushes: the registered one, or registered now. */
async function pushRegistration(isProduction: boolean): Promise<ServiceWorkerRegistration> {
  const existing = await navigator.serviceWorker.getRegistration("/");
  if (existing) {
    return existing;
  }
  const script = isProduction ? "/sw.js" : "/sw.js?push-only=1";
  await navigator.serviceWorker.register(script, { scope: "/", updateViaCache: "none" });
  return navigator.serviceWorker.ready;
}

/** This browser's subscription, if it has one (without asking anything). */
export async function existingSubscription(): Promise<PushSubscription | null> {
  if (currentPushSupport() === "unsupported") {
    return null;
  }
  const registration = await navigator.serviceWorker.getRegistration("/");
  return registration ? registration.pushManager.getSubscription() : null;
}

export type SubscribeOutcome = { ok: true; subscription: PushSubscriptionJSON } | { ok: false; reason: "denied" | "dismissed" };

/** Ask for permission (when not given yet) and subscribe with the platform's key. */
export async function subscribeThisBrowser(publicKey: string, isProduction: boolean): Promise<SubscribeOutcome> {
  const permission = Notification.permission === "granted" ? "granted" : await Notification.requestPermission();
  if (permission !== "granted") {
    return { ok: false, reason: permission === "denied" ? "denied" : "dismissed" };
  }
  const registration = await pushRegistration(isProduction);
  let subscription = await registration.pushManager.getSubscription();
  if (subscription && !isSubscribedWithKey(subscription, publicKey)) {
    await subscription.unsubscribe();
    subscription = null;
  }
  subscription ??= await registration.pushManager.subscribe({
    userVisibleOnly: true,
    applicationServerKey: applicationServerKey(publicKey),
  });
  return { ok: true, subscription: subscription.toJSON() };
}
