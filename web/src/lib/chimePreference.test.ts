import { afterEach, describe, expect, it, vi } from "vitest";

import { CHIME_STORAGE_KEY, readChimePreference, subscribeChimePreference, writeChimePreference } from "./chimePreference";

/** A browser window with localStorage and storage events (tests run in Node). */
function fakeWindow(options: { refuses?: boolean } = {}) {
  const values = new Map<string, string>();
  const refuse = () => {
    throw new Error("denied");
  };
  const target = new EventTarget();
  const localStorage = {
    getItem: options.refuses ? refuse : (key: string) => values.get(key) ?? null,
    setItem: options.refuses ? refuse : (key: string, value: string) => void values.set(key, value),
    removeItem: (key: string) => void values.delete(key),
  };
  const fake = {
    localStorage,
    addEventListener: target.addEventListener.bind(target),
    removeEventListener: target.removeEventListener.bind(target),
    dispatchStorage: (key: string) => target.dispatchEvent(Object.assign(new Event("storage"), { key })),
  };
  vi.stubGlobal("window", fake);
  return { fake, values };
}

afterEach(() => {
  vi.unstubAllGlobals();
});

describe("the chime preference", () => {
  it("is off until turned on, and tells its listeners", () => {
    const { fake, values } = fakeWindow();
    const listener = vi.fn();
    const unsubscribe = subscribeChimePreference(listener);

    expect(readChimePreference()).toBe(false);
    writeChimePreference(true);
    expect(readChimePreference()).toBe(true);
    expect(values.get(CHIME_STORAGE_KEY)).toBe("on");
    writeChimePreference(false);
    expect(readChimePreference()).toBe(false);
    expect(listener).toHaveBeenCalledTimes(2);

    fake.dispatchStorage(CHIME_STORAGE_KEY);
    fake.dispatchStorage("other");
    expect(listener).toHaveBeenCalledTimes(3);
    unsubscribe();
    writeChimePreference(true);
    expect(listener).toHaveBeenCalledTimes(3);
  });

  it("survives a browser that refuses storage", () => {
    fakeWindow({ refuses: true });

    expect(() => writeChimePreference(true)).not.toThrow();
    expect(readChimePreference()).toBe(false);
  });

  it("is off where there is no window (rendering on the server)", () => {
    const listener = vi.fn();
    const unsubscribe = subscribeChimePreference(listener);

    expect(readChimePreference()).toBe(false);
    writeChimePreference(true);
    unsubscribe();
    expect(listener).toHaveBeenCalledTimes(1);
  });
});
