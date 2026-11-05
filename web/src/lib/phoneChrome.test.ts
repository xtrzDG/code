import { describe, expect, it, vi } from "vitest";

import { ChromeStore, chromeSnapshot, type ChromeEntry } from "./phoneChrome";

type Entry = ChromeEntry<string, string>;

const fab = (label: string) => ({ label, icon: "plus", run: () => undefined });

describe("chromeSnapshot", () => {
  it("is empty without registrations", () => {
    expect(chromeSnapshot<string, string>([])).toEqual({ descriptions: [], live: null, fab: null });
  });

  it("lists the section's description before the page's", () => {
    const entries: Entry[] = [
      { level: 2, description: { title: "Channels", text: "Where customers write." } },
      { level: 1, description: { title: "Assistant", text: "Try and teach it." } },
      { level: 2, live: { updatedAt: 5, isFetching: false } },
    ];

    expect(chromeSnapshot(entries).descriptions.map((description) => description.title)).toEqual(["Assistant", "Channels"]);
  });

  it("gives the floating button and the live dot to the deepest level", () => {
    const entries: Entry[] = [
      { level: 1, fab: fab("Apply changes"), live: { updatedAt: 1, isFetching: false } },
      { level: 2, fab: fab("Add an item") },
      { level: 2, live: { updatedAt: 9, isFetching: true } },
    ];

    const snapshot = chromeSnapshot(entries);

    expect(snapshot.fab?.label).toBe("Add an item");
    expect(snapshot.live).toEqual({ updatedAt: 9, isFetching: true });
  });

  it("lets a page hide the section's button with null, while undefined says nothing", () => {
    const section: Entry = { level: 1, fab: fab("Apply changes") };

    expect(chromeSnapshot([section, { level: 2, fab: null }]).fab).toBeNull();
    expect(chromeSnapshot([section, { level: 2, fab: undefined }]).fab?.label).toBe("Apply changes");
  });

  it("prefers the later registration of the same level", () => {
    expect(chromeSnapshot<string, string>([{ level: 1, fab: fab("First") }, { level: 1, fab: fab("Second") }]).fab?.label).toBe(
      "Second",
    );
  });
});

describe("ChromeStore", () => {
  it("publishes a new snapshot to its listeners on every change", () => {
    const store = new ChromeStore<string, string>();
    const listener = vi.fn();
    const unsubscribe = store.subscribe(listener);

    store.set("header", { level: 1, description: { title: "Bookings", text: "Every booking." } });
    const first = store.getSnapshot();
    store.set("button", { level: 1, fab: fab("New booking") });

    expect(listener).toHaveBeenCalledTimes(2);
    expect(store.getSnapshot()).not.toBe(first);
    expect(store.getSnapshot().fab?.label).toBe("New booking");

    store.remove("button");
    expect(store.getSnapshot().fab).toBeNull();
    expect(listener).toHaveBeenCalledTimes(3);

    unsubscribe();
    store.remove("header");
    expect(listener).toHaveBeenCalledTimes(3);
    expect(store.getSnapshot().descriptions).toEqual([]);
  });

  it("keeps its snapshot when an unknown registration is removed", () => {
    const store = new ChromeStore<string, string>();
    const listener = vi.fn();
    store.subscribe(listener);
    const before = store.getSnapshot();

    store.remove("nobody");

    expect(store.getSnapshot()).toBe(before);
    expect(listener).not.toHaveBeenCalled();
  });
});
