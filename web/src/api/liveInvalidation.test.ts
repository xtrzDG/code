import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import { LiveInvalidation } from "./liveInvalidation";
import type { QueryKey } from "./queryKey";

const COUNTS: QueryKey = ["inbox", "b1"];

function harness(visible: { value: boolean }) {
  const calls: { key: QueryKey; refetchActive: boolean }[] = [];
  const live = new LiveInvalidation({
    alwaysFresh: [COUNTS],
    invalidate: (key, options) => calls.push({ key, refetchActive: options.refetchActive }),
    isVisible: () => visible.value,
  });
  return { live, calls };
}

beforeEach(() => vi.useFakeTimers());
afterEach(() => vi.useRealTimers());

describe("live invalidation", () => {
  it("reloads each touched key once per burst", () => {
    const { live, calls } = harness({ value: true });

    live.add([COUNTS, ["leads", "b1"]]);
    live.add([["leads", "b1"], ["inbox", "b1", "counts"]]);
    expect(calls).toEqual([]);
    vi.advanceTimersByTime(200);

    expect(calls).toEqual([
      { key: COUNTS, refetchActive: true },
      { key: ["leads", "b1"], refetchActive: true },
      { key: ["inbox", "b1", "counts"], refetchActive: true },
    ]);
  });

  it("keeps a hidden tab to the counts and catches up when it is shown", () => {
    const visible = { value: false };
    const { live, calls } = harness(visible);

    live.add([COUNTS, ["bookings", "b1"]]);
    vi.advanceTimersByTime(200);
    expect(calls).toEqual([
      { key: COUNTS, refetchActive: true },
      { key: ["bookings", "b1"], refetchActive: false },
    ]);

    live.resume();
    expect(calls).toHaveLength(2);
    visible.value = true;
    live.resume();
    live.resume();
    expect(calls.slice(2)).toEqual([{ key: ["bookings", "b1"], refetchActive: true }]);
  });

  it("forgets everything when disposed", () => {
    const { live, calls } = harness({ value: true });

    live.add([COUNTS]);
    live.dispose();
    vi.advanceTimersByTime(1_000);

    expect(calls).toEqual([]);
  });
});
