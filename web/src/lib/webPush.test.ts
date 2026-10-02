import { describe, expect, it } from "vitest";

import {
  applicationServerKey,
  isEndpointRememberedElsewhere,
  isSubscribedWithKey,
  pushSupportOf,
  readRememberedDevice,
  rememberDevice,
  subscribePushState,
  subscriptionBody,
} from "./webPush";

const PUBLIC_KEY = "BP4z9KsN6nGRTbVYI_c7VJSPQTBtkgcy27mlmlMoZIIgDll6e3vCYLocInmYWAmS6TlzAC8wEqKK6PBru3jl7A8";

class MemoryStorage {
  readonly items = new Map<string, string>();
  get length() {
    return this.items.size;
  }
  key(index: number) {
    return [...this.items.keys()][index] ?? null;
  }
  clear() {
    this.items.clear();
  }
  getItem(key: string) {
    return this.items.get(key) ?? null;
  }
  setItem(key: string, value: string) {
    this.items.set(key, value);
  }
  removeItem(key: string) {
    this.items.delete(key);
  }
}

describe("web push", () => {
  it("knows when a browser cannot notify or was blocked", () => {
    const full = { hasServiceWorker: true, hasPushManager: true, permission: "default" as const };
    expect(pushSupportOf(full)).toBe("supported");
    expect(pushSupportOf({ ...full, permission: "granted" })).toBe("supported");
    expect(pushSupportOf({ ...full, permission: "denied" })).toBe("denied");
    expect(pushSupportOf({ ...full, hasPushManager: false })).toBe("unsupported");
    expect(pushSupportOf({ ...full, permission: null })).toBe("unsupported");
  });

  it("decodes the VAPID key into the 65 bytes of a P-256 point", () => {
    const bytes = applicationServerKey(PUBLIC_KEY);
    expect(bytes).toHaveLength(65);
    expect(bytes[0]).toBe(4);
  });

  it("sends a subscription with both keys only", () => {
    const subscription = { endpoint: "https://fcm.googleapis.com/fcm/send/x", keys: { p256dh: "p", auth: "a" } };
    expect(subscriptionBody(subscription, "ka")).toEqual({ ...subscription, language: "ka" });
    expect(subscriptionBody({ endpoint: "https://x", keys: { p256dh: "p" } }, "ka")).toBeNull();
    expect(subscriptionBody({ keys: { p256dh: "p", auth: "a" } }, "ka")).toBeNull();
  });

  it("notices a subscription made with another server key", () => {
    const withKey = (key: Uint8Array | null) =>
      ({ options: { applicationServerKey: key ? key.buffer : null } }) as unknown as PushSubscription;
    expect(isSubscribedWithKey(withKey(applicationServerKey(PUBLIC_KEY)), PUBLIC_KEY)).toBe(true);
    expect(isSubscribedWithKey(withKey(new Uint8Array(65)), PUBLIC_KEY)).toBe(false);
    expect(isSubscribedWithKey(withKey(null), PUBLIC_KEY)).toBe(true);
  });

  it("remembers which device this browser is, per business", () => {
    const storage = new MemoryStorage();
    rememberDevice(storage, "business_1", { endpoint: "https://e", deviceId: "push_subscription_1" });
    expect(readRememberedDevice(storage, "business_1")).toEqual({ endpoint: "https://e", deviceId: "push_subscription_1" });
    expect(readRememberedDevice(storage, "business_2")).toBeNull();
    storage.setItem("aw_push_device:business_3", "{broken");
    expect(readRememberedDevice(storage, "business_3")).toBeNull();
    storage.setItem("aw_push_device:business_4", JSON.stringify({ endpoint: 1, deviceId: "x" }));
    expect(readRememberedDevice(storage, "business_4")).toBeNull();
    rememberDevice(storage, "business_1", null);
    expect(readRememberedDevice(storage, "business_1")).toBeNull();
    expect(readRememberedDevice(null, "business_1")).toBeNull();
    const failing = {
      getItem: () => {
        throw new Error("blocked");
      },
      setItem: () => {
        throw new Error("blocked");
      },
      removeItem: () => undefined,
    };
    expect(readRememberedDevice(failing, "business_1")).toBeNull();
    expect(() => rememberDevice(failing, "business_1", { endpoint: "e", deviceId: "d" })).not.toThrow();
  });

  it("keeps the browser's one subscription while another business uses it", () => {
    const storage = new MemoryStorage() as unknown as Storage;
    let changes = 0;
    const stop = subscribePushState(() => (changes += 1));
    rememberDevice(storage, "business_1", { endpoint: "https://e", deviceId: "d1" });
    rememberDevice(storage, "business_2", { endpoint: "https://e", deviceId: "d2" });
    stop();
    rememberDevice(storage, "business_3", { endpoint: "https://other", deviceId: "d3" });

    expect(changes).toBe(2);
    expect(isEndpointRememberedElsewhere(storage, "business_1", "https://e")).toBe(true);
    expect(isEndpointRememberedElsewhere(storage, "business_3", "https://other")).toBe(false);
    expect(isEndpointRememberedElsewhere(null, "business_3", "https://other")).toBe(true);
  });
});
