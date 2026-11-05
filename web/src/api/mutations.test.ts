import { describe, expect, it, vi } from "vitest";

import { executeMutation } from "./mutations";
import { QueryCache } from "./queryCache";
import type { ApiResult } from "./result";

function ok<T>(data: T): Promise<ApiResult<T>> {
  return Promise.resolve({ data, response: new Response(JSON.stringify(data), { status: 200 }) });
}

function fail(status: number, body: unknown): Promise<ApiResult<never>> {
  return Promise.resolve({ error: body, response: new Response(JSON.stringify(body), { status }) });
}

const LIST = ["leads", "b1", "list", "all"] as const;

async function cacheWithLead(status: string) {
  const cache = new QueryCache();
  await cache.fetch(LIST, async () => [{ id: "lead_1", status }]);
  return cache;
}

const setStatus = (cache: QueryCache, status: string) => () =>
  cache.update<{ id: string; status: string }[]>(["leads", "b1"], (leads) => leads.map((lead) => ({ ...lead, status })));

describe("executeMutation", () => {
  it("shows the optimistic change at once and keeps it when the call succeeds", async () => {
    const cache = await cacheWithLead("new");
    let seenDuringCall: unknown;
    const result = await executeMutation(
      () => {
        seenDuringCall = cache.get(LIST).data;
        return ok({ status: "won" });
      },
      { optimistic: setStatus(cache, "won") },
      [],
      cache,
    );
    expect(result).toEqual({ ok: true, data: { status: "won" } });
    expect(seenDuringCall).toEqual([{ id: "lead_1", status: "won" }]);
    expect(cache.get(LIST).data).toEqual([{ id: "lead_1", status: "won" }]);
  });

  it("rolls the change back when the API refuses, and reports the error", async () => {
    const cache = await cacheWithLead("new");
    const rollback = vi.fn();
    const result = await executeMutation(
      () => fail(500, { error: "internal_error", message: "Boom." }),
      { optimistic: setStatus(cache, "won"), rollback },
      ["lead_1"],
      cache,
    );
    expect(result.ok).toBe(false);
    expect(!result.ok && result.error.code).toBe("internal_error");
    expect(cache.get(LIST).data).toEqual([{ id: "lead_1", status: "new" }]);
    expect(rollback).toHaveBeenCalledWith(expect.objectContaining({ status: 500 }), "lead_1");
  });

  it("rolls back when the network fails before any answer", async () => {
    const cache = await cacheWithLead("new");
    const result = await executeMutation(() => Promise.reject(new TypeError("Failed to fetch")), { optimistic: setStatus(cache, "lost") }, [], cache);
    expect(!result.ok && result.error.code).toBe("network_error");
    expect(cache.get(LIST).data).toEqual([{ id: "lead_1", status: "new" }]);
  });

  it("invalidates the given keys after success and after failure", async () => {
    const cache = new QueryCache();
    await cache.fetch(["dashboard", "b1"], async () => "stats");
    await executeMutation(() => ok("done"), { invalidate: [["dashboard", "b1"]] }, [], cache);
    expect(cache.get(["dashboard", "b1"]).isInvalidated).toBe(true);

    await cache.fetch(["dashboard", "b1"], async () => "stats again");
    await executeMutation(() => fail(409, { error: "conflict", message: "Taken." }), { invalidate: () => [["dashboard"]] }, [], cache);
    expect(cache.get(["dashboard", "b1"]).isInvalidated).toBe(true);
  });

  it("marks `stale` keys without reloading the one on screen", async () => {
    const cache = new QueryCache();
    const fetcher = vi.fn().mockResolvedValue(["lead"]);
    const unsubscribe = cache.subscribe(LIST, () => undefined);
    await cache.fetch(LIST, fetcher);
    await executeMutation(() => ok("done"), { stale: [["leads", "b1"]] }, [], cache);
    expect(fetcher).toHaveBeenCalledTimes(1);
    expect(cache.get(LIST).isInvalidated).toBe(true);
    unsubscribe();
  });
});
