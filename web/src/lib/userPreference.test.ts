import { afterEach, describe, expect, it, vi } from "vitest";

import {
  browserStorage,
  parseNameSet,
  preferenceKey,
  readPreference,
  subscribePreferences,
  toggledNameSet,
  writePreference,
  type PreferenceStorage,
} from "./userPreference";

function memoryStorage(): PreferenceStorage & { data: Map<string, string> } {
  const data = new Map<string, string>();
  return {
    data,
    getItem: (key) => data.get(key) ?? null,
    setItem: (key, value) => void data.set(key, value),
    removeItem: (key) => void data.delete(key),
  };
}

const refusing: PreferenceStorage = {
  getItem: () => {
    throw new Error("blocked");
  },
  setItem: () => {
    throw new Error("blocked");
  },
  removeItem: () => {
    throw new Error("blocked");
  },
};

afterEach(() => {
  vi.unstubAllGlobals();
});

describe("user preferences", () => {
  it("keeps each person's choice under their own key", () => {
    const storage = memoryStorage();
    writePreference(storage, "inbox-density", "user_a", "compact");
    expect(storage.data.get(preferenceKey("inbox-density", "user_a"))).toBe("compact");
    expect(readPreference(storage, "inbox-density", "user_a")).toBe("compact");
    expect(readPreference(storage, "inbox-density", "user_b")).toBeNull();
  });

  it("forgets a choice set to null", () => {
    const storage = memoryStorage();
    writePreference(storage, "inbox-width", "user_a", "400");
    writePreference(storage, "inbox-width", "user_a", null);
    expect(readPreference(storage, "inbox-width", "user_a")).toBeNull();
  });

  it("reads the default and keeps working when storage refuses or is missing", () => {
    expect(readPreference(refusing, "inbox-density", "user_a")).toBeNull();
    expect(() => writePreference(refusing, "inbox-density", "user_a", "compact")).not.toThrow();
    expect(() => writePreference(refusing, "inbox-density", "user_a", null)).not.toThrow();
    expect(readPreference(null, "inbox-density", "user_a")).toBeNull();
  });

  it("tells this tab's listeners about a change, until they leave", () => {
    const listener = vi.fn();
    const leave = subscribePreferences(listener);
    writePreference(memoryStorage(), "inbox-density", "user_a", "compact");
    expect(listener).toHaveBeenCalledTimes(1);
    leave();
    writePreference(memoryStorage(), "inbox-density", "user_a", "comfortable");
    expect(listener).toHaveBeenCalledTimes(1);
  });

  it("follows another tab's change of a preference, and ignores other keys", () => {
    const target = new EventTarget();
    vi.stubGlobal("window", target);
    const listener = vi.fn();
    const leave = subscribePreferences(listener);
    const storageEvent = (key: string | null) => Object.assign(new Event("storage"), { key });
    target.dispatchEvent(storageEvent(preferenceKey("inbox-density", "user_a")));
    target.dispatchEvent(storageEvent(null));
    target.dispatchEvent(storageEvent("aw.chime.needsPerson"));
    expect(listener).toHaveBeenCalledTimes(2);
    leave();
    target.dispatchEvent(storageEvent(preferenceKey("inbox-density", "user_a")));
    expect(listener).toHaveBeenCalledTimes(2);
  });

  it("finds the browser's storage only in a browser that allows it", () => {
    expect(browserStorage()).toBeNull();
    const storage = memoryStorage();
    vi.stubGlobal("window", { localStorage: storage });
    expect(browserStorage()).toBe(storage);
    vi.stubGlobal("window", {
      get localStorage(): Storage {
        throw new Error("SecurityError");
      },
    });
    expect(browserStorage()).toBeNull();
  });
});

describe("name sets", () => {
  it("parse the stored names and skip anything else", () => {
    expect([...parseNameSet("stats,topics")]).toEqual(["stats", "topics"]);
    expect([...parseNameSet(null)]).toEqual([]);
    expect([...parseNameSet("stats,,<script>,Topics,chart-2")]).toEqual(["stats", "chart-2"]);
  });

  it("add and remove a name, in a stable order, and empty to null", () => {
    expect(toggledNameSet(null, "topics", true)).toBe("topics");
    expect(toggledNameSet("topics", "stats", true)).toBe("stats,topics");
    expect(toggledNameSet("stats,topics", "stats", true)).toBe("stats,topics");
    expect(toggledNameSet("stats,topics", "stats", false)).toBe("topics");
    expect(toggledNameSet("topics", "topics", false)).toBeNull();
  });
});
