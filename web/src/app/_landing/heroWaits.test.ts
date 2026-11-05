// @vitest-environment jsdom
import { afterEach, describe, expect, it, vi } from "vitest";

import { afterNextPaint, afterPageLoad, hasWebGl, readDeviceSignals, whenIdle, whenOnScreen } from "./heroWaits";

afterEach(() => {
  vi.restoreAllMocks();
  vi.unstubAllGlobals();
  vi.useRealTimers();
});

function stubMatchMedia(matching: readonly string[]) {
  vi.stubGlobal("matchMedia", (query: string) => ({ matches: matching.includes(query), media: query }) as MediaQueryList);
}

describe("what the device tells", () => {
  it("reads motion, layout, pointer, cores, memory and the connection", () => {
    stubMatchMedia(["(min-width: 64rem)", "(pointer: coarse)"]);
    vi.spyOn(navigator, "hardwareConcurrency", "get").mockReturnValue(8);
    Object.defineProperty(navigator, "deviceMemory", { value: 4, configurable: true });
    Object.defineProperty(navigator, "connection", { value: { saveData: true, effectiveType: "3g" }, configurable: true });

    expect(readDeviceSignals()).toEqual({
      prefersReducedMotion: false,
      isWideLayout: true,
      isCoarsePointer: true,
      cores: 8,
      memoryGb: 4,
      saveData: true,
      effectiveType: "3g",
    });
  });

  it("leaves out what the browser hides", () => {
    stubMatchMedia(["(prefers-reduced-motion: reduce)"]);
    vi.spyOn(navigator, "hardwareConcurrency", "get").mockReturnValue(0);
    Object.defineProperty(navigator, "deviceMemory", { value: undefined, configurable: true });
    Object.defineProperty(navigator, "connection", { value: undefined, configurable: true });

    expect(readDeviceSignals()).toEqual({
      prefersReducedMotion: true,
      isWideLayout: false,
      isCoarsePointer: false,
      cores: undefined,
      memoryGb: undefined,
      saveData: undefined,
      effectiveType: undefined,
    });
  });
});

describe("the WebGL probe", () => {
  it("creates a context, releases it at once and reports success", () => {
    const loseContext = vi.fn();
    // getContext is overloaded per kind of context; the probe asks for WebGL.
    vi.spyOn(HTMLCanvasElement.prototype, "getContext").mockReturnValue({ getExtension: () => ({ loseContext }) } as never);
    expect(hasWebGl()).toBe(true);
    expect(loseContext).toHaveBeenCalledTimes(1);
  });

  it("reports no WebGL when there is no context or creating one fails", () => {
    const getContext = vi.spyOn(HTMLCanvasElement.prototype, "getContext").mockReturnValue(null);
    expect(hasWebGl()).toBe(false);
    getContext.mockImplementation(() => {
      throw new Error("blocked");
    });
    expect(hasWebGl()).toBe(false);
  });
});

describe("the moments the scene waits for", () => {
  it("after the next painted frame", () => {
    vi.useFakeTimers({ toFake: ["requestAnimationFrame", "cancelAnimationFrame", "setTimeout", "clearTimeout"] });
    const next = vi.fn();
    afterNextPaint(next);
    vi.advanceTimersToNextFrame();
    expect(next).not.toHaveBeenCalled();
    vi.runOnlyPendingTimers();
    expect(next).toHaveBeenCalledTimes(1);

    const cancelled = vi.fn();
    afterNextPaint(cancelled)();
    vi.advanceTimersToNextFrame();
    vi.runOnlyPendingTimers();
    expect(cancelled).not.toHaveBeenCalled();
  });

  it("once the page has loaded: at once when it has, else on the load event", () => {
    const loaded = vi.fn();
    afterPageLoad(loaded);
    expect(document.readyState).toBe("complete");
    expect(loaded).toHaveBeenCalledTimes(1);

    vi.spyOn(document, "readyState", "get").mockReturnValue("interactive");
    const later = vi.fn();
    const cancelled = vi.fn();
    afterPageLoad(later);
    afterPageLoad(cancelled)();
    expect(later).not.toHaveBeenCalled();
    window.dispatchEvent(new Event("load"));
    expect(later).toHaveBeenCalledTimes(1);
    expect(cancelled).not.toHaveBeenCalled();
  });

  it("when the browser is idle, with a deadline", () => {
    const callbacks: (() => void)[] = [];
    const requestIdleCallback = vi.fn((callback: () => void) => callbacks.push(callback));
    const cancelIdleCallback = vi.fn();
    vi.stubGlobal("requestIdleCallback", requestIdleCallback);
    vi.stubGlobal("cancelIdleCallback", cancelIdleCallback);

    const next = vi.fn();
    const cancel = whenIdle(next);
    expect(requestIdleCallback).toHaveBeenCalledWith(expect.any(Function), { timeout: 4000 });
    callbacks[0]?.();
    expect(next).toHaveBeenCalledTimes(1);
    cancel();
    expect(cancelIdleCallback).toHaveBeenCalledWith(1);
  });

  it("after a short while where the browser cannot tell when it is idle", () => {
    vi.useFakeTimers({ toFake: ["setTimeout", "clearTimeout"] });
    const next = vi.fn();
    whenIdle(next);
    vi.advanceTimersByTime(299);
    expect(next).not.toHaveBeenCalled();
    vi.advanceTimersByTime(1);
    expect(next).toHaveBeenCalledTimes(1);

    const cancelled = vi.fn();
    whenIdle(cancelled)();
    vi.advanceTimersByTime(300);
    expect(cancelled).not.toHaveBeenCalled();
  });

  it("when the hero is on screen (or nearly), once", () => {
    const observers: { callback: IntersectionObserverCallback; options?: IntersectionObserverInit; disconnect: ReturnType<typeof vi.fn> }[] = [];
    vi.stubGlobal(
      "IntersectionObserver",
      class {
        disconnect = vi.fn();
        constructor(callback: IntersectionObserverCallback, options?: IntersectionObserverInit) {
          observers.push({ callback, options, disconnect: this.disconnect });
        }
        observe() {}
      },
    );
    const next = vi.fn();
    const cancel = whenOnScreen(document.body)(next);
    const [observer] = observers;
    expect(observer?.options).toEqual({ rootMargin: "200px" });

    const seen = (isIntersecting: boolean) =>
      observer?.callback([{ isIntersecting } as IntersectionObserverEntry], {} as IntersectionObserver);
    seen(false);
    expect(next).not.toHaveBeenCalled();
    seen(true);
    expect(next).toHaveBeenCalledTimes(1);
    expect(observer?.disconnect).toHaveBeenCalled();
    cancel();
    expect(observer?.disconnect).toHaveBeenCalledTimes(2);
  });

  it("at once when there is nothing to watch", () => {
    const next = vi.fn();
    whenOnScreen(null)(next)();
    expect(next).toHaveBeenCalledTimes(1);
  });
});
