/**
 * The browser's side of the hero's loading rules (lib/heroDevice.ts): what
 * the device tells about itself, and the moments the 3D scene waits for
 * (lib/waits.ts). Browser only: HeroVisual calls these from effects.
 */

import type { DeviceSignals } from "@/lib/heroDevice";
import type { Wait } from "@/lib/waits";

export const REDUCED_MOTION_QUERY = "(prefers-reduced-motion: reduce)";
/** Tailwind's `lg`: the layout where the scene stands beside the headline. */
export const WIDE_LAYOUT_QUERY = "(min-width: 64rem)";

/** How long the browser may stay busy before the scene loads anyway. */
const IDLE_TIMEOUT_MS = 4000;
/** Start loading a little before the hero scrolls back into view. */
const ON_SCREEN_MARGIN = "200px";

interface NetworkInformation {
  saveData?: boolean;
  effectiveType?: string;
}

export function readDeviceSignals(): DeviceSignals {
  const browser = navigator as Navigator & { deviceMemory?: number; connection?: NetworkInformation };
  return {
    prefersReducedMotion: window.matchMedia(REDUCED_MOTION_QUERY).matches,
    isWideLayout: window.matchMedia(WIDE_LAYOUT_QUERY).matches,
    isCoarsePointer: window.matchMedia("(pointer: coarse)").matches,
    cores: browser.hardwareConcurrency || undefined,
    memoryGb: browser.deviceMemory,
    saveData: browser.connection?.saveData,
    effectiveType: browser.connection?.effectiveType,
  };
}

/** Whether a WebGL context can be created (and the probe's is released at once). */
export function hasWebGl(): boolean {
  try {
    const probe = document.createElement("canvas");
    const context = probe.getContext("webgl2") ?? probe.getContext("webgl");
    context?.getExtension("WEBGL_lose_context")?.loseContext();
    return context !== null;
  } catch {
    return false;
  }
}

/** After the next frame is painted (the first one, right after hydration). */
export const afterNextPaint: Wait = (next) => {
  let timer: ReturnType<typeof setTimeout> | undefined;
  const frame = requestAnimationFrame(() => {
    timer = setTimeout(next, 0);
  });
  return () => {
    cancelAnimationFrame(frame);
    clearTimeout(timer);
  };
};

/** Once the page and everything it loads have arrived (the `load` event). */
export const afterPageLoad: Wait = (next) => {
  if (document.readyState === "complete") {
    next();
    return () => undefined;
  }
  const onLoad = () => next();
  window.addEventListener("load", onLoad, { once: true });
  return () => window.removeEventListener("load", onLoad);
};

/** When the browser has nothing else to do (or after a while, where it cannot tell). */
export const whenIdle: Wait = (next) => {
  if ("requestIdleCallback" in window) {
    const handle = window.requestIdleCallback(() => next(), { timeout: IDLE_TIMEOUT_MS });
    return () => window.cancelIdleCallback(handle);
  }
  const timer = setTimeout(next, 300);
  return () => clearTimeout(timer);
};

/** When `element` is on screen (or nearly). */
export function whenOnScreen(element: Element | null): Wait {
  return (next) => {
    if (element === null || !("IntersectionObserver" in window)) {
      next();
      return () => undefined;
    }
    const observer = new IntersectionObserver(
      (entries) => {
        if (entries.some((entry) => entry.isIntersecting)) {
          observer.disconnect();
          next();
        }
      },
      { rootMargin: ON_SCREEN_MARGIN },
    );
    observer.observe(element);
    return () => observer.disconnect();
  };
}
