import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import { ApiError } from "./errors";
import { QueryCache } from "./queryCache";
import { startsWithKey } from "./queryKey";

/** A fetcher whose answers the test releases one by one. */
function deferredFetcher<T>() {
  const pending: { resolve: (value: T) => void; reject: (error: unknown) => void }[] = [];
  const fetcher = vi.fn(
    () =>
      new Promise<T>((resolve, reject) => {
        pending.push({ resolve, reject });
      }),
  );
  return { fetcher, pending };
}

const flush = () => new Promise((resolve) => setTimeout(resolve, 0));

describe("QueryCache", () => {
  let now = 1_000_000;
  let cache: QueryCache;

  beforeEach(() => {
    now = 1_000_000;
    cache = new QueryCache({ now: () => now, gcMs: 60_000 });
  });

  afterEach(() => {
    vi.useRealTimers();
  });

  it("shares one request between readers of the same key (dedupe)", async () => {
    const { fetcher, pending } = deferredFetcher<string>();
    const first = cache.fetch(["leads", "b1"], fetcher);
    const second = cache.fetch(["leads", "b1"], fetcher);
    await flush();
    expect(fetcher).toHaveBeenCalledTimes(1);
    expect(cache.get(["leads", "b1"]).isFetching).toBe(true);

    pending[0].resolve("leads");
    await Promise.all([first, second]);
    expect(cache.get(["leads", "b1"])).toMatchObject({ data: "leads", error: null, isFetching: false, updatedAt: now });
  });

  it("serves fresh data without a request and revalidates stale data behind it", async () => {
    const fetcher = vi.fn().mockResolvedValueOnce("v1").mockResolvedValueOnce("v2");
    await cache.fetch(["dashboard", "b1"], fetcher, { staleMs: 30_000 });

    now += 10_000;
    await cache.fetch(["dashboard", "b1"], fetcher, { staleMs: 30_000 });
    expect(fetcher).toHaveBeenCalledTimes(1);

    now += 30_000;
    const revalidation = cache.fetch(["dashboard", "b1"], fetcher, { staleMs: 30_000 });
    // The old data stays readable while the fresh copy loads (stale-while-revalidate).
    expect(cache.get(["dashboard", "b1"])).toMatchObject({ data: "v1", isFetching: true });
    await revalidation;
    expect(cache.get(["dashboard", "b1"]).data).toBe("v2");
    expect(fetcher).toHaveBeenCalledTimes(2);
  });

  it("keeps the shown data when a reload fails, with the error next to it", async () => {
    const failure = new ApiError({ status: 503, code: "backend_unavailable" });
    const fetcher = vi.fn().mockResolvedValueOnce("shown").mockRejectedValueOnce(failure);
    await cache.fetch(["billing", "b1"], fetcher);
    await cache.fetch(["billing", "b1"], fetcher, { force: true });
    expect(cache.get(["billing", "b1"])).toMatchObject({ data: "shown", error: failure, isFetching: false });
  });

  it("drops an answer that started before a local write (it would undo the write)", async () => {
    const { fetcher, pending } = deferredFetcher<string>();
    const load = cache.fetch(["leads", "b1"], fetcher);
    await flush();
    cache.setData(["leads", "b1"], "written locally");
    pending[0].resolve("older server copy");
    await load;
    expect(cache.get(["leads", "b1"])).toMatchObject({ data: "written locally", isInvalidated: true, isFetching: false });
  });

  it("keeps only the newest of two overlapping loads", async () => {
    const { fetcher, pending } = deferredFetcher<string>();
    const first = cache.fetch(["leads", "b1"], fetcher);
    await flush();
    const second = cache.fetch(["leads", "b1"], fetcher, { force: true });
    await flush();
    pending[1].resolve("new");
    pending[0].resolve("old");
    await Promise.all([first, second]);
    expect(cache.get(["leads", "b1"]).data).toBe("new");
  });

  it("notifies subscribers with a new snapshot on every change", async () => {
    const listener = vi.fn();
    const unsubscribe = cache.subscribe(["channels", "b1"], listener);
    const before = cache.get(["channels", "b1"]);
    await cache.fetch(["channels", "b1"], async () => "channels");
    expect(listener).toHaveBeenCalled();
    expect(cache.get(["channels", "b1"])).not.toBe(before);
    unsubscribe();
  });

  describe("invalidate", () => {
    it("reloads the keys on screen under the prefix at once", async () => {
      const fetcher = vi.fn().mockResolvedValueOnce("before").mockResolvedValueOnce("after");
      const unsubscribe = cache.subscribe(["leads", "b1", "list", "all", false], () => undefined);
      await cache.fetch(["leads", "b1", "list", "all", false], fetcher, { staleMs: 60_000 });

      cache.invalidate(["leads", "b1"]);
      await flush();
      expect(fetcher).toHaveBeenCalledTimes(2);
      expect(cache.get(["leads", "b1", "list", "all", false]).data).toBe("after");
      unsubscribe();
    });

    it("marks keys nobody shows, so they reload when shown next", async () => {
      const fetcher = vi.fn().mockResolvedValueOnce("before").mockResolvedValueOnce("after");
      await cache.fetch(["leads", "b1", "list", "won", false], fetcher, { staleMs: 60_000 });

      cache.invalidate(["leads", "b1"]);
      await flush();
      expect(fetcher).toHaveBeenCalledTimes(1);
      expect(cache.get(["leads", "b1", "list", "won", false])).toMatchObject({ data: "before", isInvalidated: true });

      await cache.fetch(["leads", "b1", "list", "won", false], fetcher, { staleMs: 60_000 });
      expect(cache.get(["leads", "b1", "list", "won", false])).toMatchObject({ data: "after", isInvalidated: false });
    });

    it("leaves other businesses and sections alone", async () => {
      await cache.fetch(["leads", "b2"], async () => "other business");
      await cache.fetch(["handoffs", "b1"], async () => "other section");
      cache.invalidate(["leads", "b1"]);
      expect(cache.get(["leads", "b2"]).isInvalidated).toBe(false);
      expect(cache.get(["handoffs", "b1"]).isInvalidated).toBe(false);
    });

    it("can mark keys on screen without reloading them", async () => {
      const fetcher = vi.fn().mockResolvedValue("list");
      const unsubscribe = cache.subscribe(["handoffs", "b1"], () => undefined);
      await cache.fetch(["handoffs", "b1"], fetcher);
      cache.invalidate(["handoffs"], { refetchActive: false });
      await flush();
      expect(fetcher).toHaveBeenCalledTimes(1);
      expect(cache.get(["handoffs", "b1"]).isInvalidated).toBe(true);
      unsubscribe();
    });
  });

  describe("optimistic update and rollback", () => {
    it("changes every loaded key under the prefix and restores them on rollback", async () => {
      await cache.fetch(["leads", "b1", "list", "all"], async () => ["new"]);
      await cache.fetch(["leads", "b1", "list", "new"], async () => ["new"]);
      const rollback = cache.update<string[]>(["leads", "b1"], (statuses) => statuses.map(() => "won"));
      expect(cache.get(["leads", "b1", "list", "all"]).data).toEqual(["won"]);
      expect(cache.get(["leads", "b1", "list", "new"]).data).toEqual(["won"]);

      rollback();
      expect(cache.get(["leads", "b1", "list", "all"]).data).toEqual(["new"]);
      expect(cache.get(["leads", "b1", "list", "new"]).data).toEqual(["new"]);
    });

    it("does not roll back over newer data from the server", async () => {
      const fetcher = vi.fn().mockResolvedValueOnce(["new"]).mockResolvedValueOnce(["lost"]);
      await cache.fetch(["leads", "b1"], fetcher);
      const rollback = cache.update<string[]>(["leads", "b1"], () => ["won"]);
      await cache.fetch(["leads", "b1"], fetcher, { force: true });
      rollback();
      expect(cache.get(["leads", "b1"]).data).toEqual(["lost"]);
    });
  });

  it("forgets unobserved keys after a while, but not the ones on screen", async () => {
    vi.useFakeTimers();
    await cache.fetch(["catalog", "plans"], async () => "plans");
    const unsubscribe = cache.subscribe(["channels", "b1"], () => undefined);
    await cache.fetch(["channels", "b1"], async () => "channels");

    vi.advanceTimersByTime(60_000);
    expect(cache.get(["catalog", "plans"]).data).toBeUndefined();
    expect(cache.get(["channels", "b1"]).data).toBe("channels");

    unsubscribe();
    vi.advanceTimersByTime(60_000);
    expect(cache.size).toBe(0);
  });
});

describe("query key prefixes", () => {
  it("match whole parts from the start", () => {
    expect(startsWithKey(["leads", "b1", "list"], ["leads", "b1"])).toBe(true);
    expect(startsWithKey(["leads", "b1"], ["leads", "b1"])).toBe(true);
    expect(startsWithKey(["leads", "b10"], ["leads", "b1"])).toBe(false);
    expect(startsWithKey(["leads"], ["leads", "b1"])).toBe(false);
    expect(startsWithKey(["leads", null], ["leads", null])).toBe(true);
  });
});
