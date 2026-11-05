import { describe, expect, it, vi } from "vitest";

import { inSequence, type Wait } from "./waits";

/** A wait the test releases by hand, recording whether it was cancelled. */
function manualWait() {
  const state = { next: undefined as (() => void) | undefined, cancelled: false, started: false };
  const wait: Wait = (next) => {
    state.started = true;
    state.next = next;
    return () => {
      state.cancelled = true;
    };
  };
  return { wait, state, release: () => state.next?.() };
}

const immediate: Wait = (next) => {
  next();
  return () => undefined;
};

describe("waits in sequence", () => {
  it("starts each wait only after the one before it, then finishes", () => {
    const first = manualWait();
    const second = manualWait();
    const done = vi.fn();
    inSequence([first.wait, second.wait], done);

    expect(first.state.started).toBe(true);
    expect(second.state.started).toBe(false);
    first.release();
    expect(second.state.started).toBe(true);
    expect(done).not.toHaveBeenCalled();
    second.release();
    expect(done).toHaveBeenCalledTimes(1);
  });

  it("finishes at once without waits, or with waits that are already over", () => {
    const done = vi.fn();
    inSequence([], done);
    expect(done).toHaveBeenCalledTimes(1);

    const later = manualWait();
    const afterImmediate = vi.fn();
    inSequence([immediate, immediate, later.wait], afterImmediate);
    expect(later.state.started).toBe(true);
    later.release();
    expect(afterImmediate).toHaveBeenCalledTimes(1);
  });

  it("cancels the wait in progress and runs nothing after, even when a wait answers late", () => {
    const first = manualWait();
    const second = manualWait();
    const done = vi.fn();
    const cancel = inSequence([first.wait, second.wait], done);

    first.release();
    cancel();
    expect(second.state.cancelled).toBe(true);
    expect(first.state.cancelled).toBe(false);
    second.release();
    expect(done).not.toHaveBeenCalled();
  });

  it("ignores a wait that answers twice", () => {
    const first = manualWait();
    const second = manualWait();
    const done = vi.fn();
    inSequence([first.wait, second.wait], done);

    first.release();
    first.release();
    second.release();
    expect(done).toHaveBeenCalledTimes(1);
  });

  it("does not cancel a wait that has already moved the sequence on", () => {
    const cancelImmediate = vi.fn();
    const answered: Wait = (next) => {
      next();
      return cancelImmediate;
    };
    const pending = manualWait();
    const cancel = inSequence([answered, pending.wait], vi.fn());
    cancel();
    expect(cancelImmediate).not.toHaveBeenCalled();
    expect(pending.state.cancelled).toBe(true);
  });
});
