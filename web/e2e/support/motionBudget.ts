/**
 * The cabinet's motion budget in the browser (motion-budget.spec.ts):
 *
 *   - INP: the slowest tap's time to its next paint (Event Timing), the
 *     way Core Web Vitals reads it for a page with few interactions;
 *   - CLS: layout shifts not caused by the person's own input;
 *   - what moved: CSS animations and transitions, Web Animations
 *     (element.animate, which motion uses), styles rewritten frame after
 *     frame (motion's springs), view transitions and 3D canvases.
 *
 * Everything is recorded by an init script from the page's first moment,
 * so each `read*` sees the whole visit; nothing polls while a test acts.
 */

import type { Page } from "@playwright/test";

/** Properties whose animation moves something on screen (fading is not moving). */
const MOVING_PROPERTIES = [
  "transform",
  "translate",
  "scale",
  "rotate",
  "top",
  "left",
  "right",
  "bottom",
  "inset",
  "width",
  "height",
  "margin",
  "offset-distance",
  "offsetDistance",
];

declare global {
  interface Window {
    __awBudget?: {
      interactions: Record<number, number>;
      slowest: string;
      layoutShift: number;
      shifts: string[];
      moved: string[];
      viewTransitions: number;
      styleValues: WeakMap<Element, Set<string>>;
      /** False once the motion watch stops (startMeasuring with watchMotion false). */
      watchesMotion: boolean;
      stopWatchingMotion: () => void;
      /** When the main thread last finished a long task (ms, performance.now()). */
      lastBusy: number;
    };
  }
}

/** Starts recording interactions, layout shifts and motion on every page of `page`. */
export async function recordMotionBudget(page: Page): Promise<void> {
  await page.addInitScript((moving: string[]) => {
    const isMoving = (property: string) => moving.some((name) => property === name || property.startsWith(`${name}-`));
    const budget = {
      interactions: {} as Record<number, number>,
      slowest: "",
      layoutShift: 0,
      shifts: [] as string[],
      moved: [] as string[],
      viewTransitions: 0,
      styleValues: new WeakMap<Element, Set<string>>(),
      watchesMotion: true,
      stopWatchingMotion: () => undefined,
      lastBusy: 0,
    };
    window.__awBudget = budget;
    new PerformanceObserver((list) => {
      for (const entry of list.getEntries()) {
        budget.lastBusy = Math.max(budget.lastBusy, entry.startTime + entry.duration);
      }
    }).observe({ type: "longtask", buffered: true });

    const describe = (target: EventTarget | Node | null | undefined) =>
      target instanceof Element ? `${target.tagName.toLowerCase()}.${String(target.getAttribute("class") ?? "").slice(0, 60)}` : "?";
    new PerformanceObserver((list) => {
      for (const entry of list.getEntries() as (PerformanceEventTiming & { interactionId?: number })[]) {
        if (entry.interactionId) {
          const longest = Math.max(...Object.values(budget.interactions), 0);
          budget.interactions[entry.interactionId] = Math.max(budget.interactions[entry.interactionId] ?? 0, entry.duration);
          if (entry.duration > longest) {
            const delay = Math.round(entry.processingStart - entry.startTime);
            const handlers = Math.round(entry.processingEnd - entry.processingStart);
            const paint = Math.round(entry.startTime + entry.duration - entry.processingEnd);
            budget.slowest = `${entry.name} on ${describe(entry.target)} at ${location.pathname}: ${entry.duration} ms (input delay ${delay}, handlers ${handlers}, to paint ${paint})`;
          }
        }
      }
    }).observe({ type: "event", buffered: true, durationThreshold: 16 } as PerformanceObserverInit);
    type Shift = PerformanceEntry & { value: number; hadRecentInput: boolean; sources?: { node?: Node | null }[] };
    new PerformanceObserver((list) => {
      for (const entry of list.getEntries() as Shift[]) {
        if (!entry.hadRecentInput) {
          budget.layoutShift += entry.value;
          const nodes = (entry.sources ?? []).map((source) => describe(source.node)).join(" | ");
          budget.shifts.push(`${entry.value.toFixed(4)} at ${location.pathname}: ${nodes}`);
        }
      }
    }).observe({ type: "layout-shift", buffered: true });

    const lasts = (duration: unknown) => typeof duration === "number" && duration > 1;
    // CSS animations and transitions that really run (reduced motion cuts them to 0.01 ms).
    document.addEventListener(
      "animationstart",
      (event) => {
        if (!budget.watchesMotion) {
          return;
        }
        const target = event.target as Element;
        for (const animation of target.getAnimations?.() ?? []) {
          const effect = animation.effect as KeyframeEffect | null;
          const keyframes = effect?.getKeyframes() ?? [];
          if (lasts(effect?.getComputedTiming().duration) && keyframes.some((frame) => Object.keys(frame).some(isMoving))) {
            budget.moved.push(`css animation ${event.animationName} on ${describe(target)}`);
          }
        }
      },
      true,
    );
    document.addEventListener(
      "transitionstart",
      (event) => {
        if (!budget.watchesMotion) {
          return;
        }
        const target = event.target as Element;
        const running = (target.getAnimations?.() ?? []).find(
          (animation) => (animation as CSSTransition).transitionProperty === event.propertyName,
        );
        if (isMoving(event.propertyName) && lasts(running?.effect?.getComputedTiming().duration)) {
          budget.moved.push(`css transition ${event.propertyName} on ${describe(target)}`);
        }
      },
      true,
    );
    // Web Animations (motion's hardware-accelerated path, the badge's beat).
    const animate = Element.prototype.animate;
    Element.prototype.animate = function (this: Element, keyframes, options) {
      const frames = Array.isArray(keyframes) ? keyframes : keyframes ? [keyframes] : [];
      const duration = typeof options === "number" ? options : options?.duration;
      const properties = frames.flatMap((frame) => Object.keys(frame ?? {}));
      if (budget.watchesMotion && lasts(duration) && properties.some(isMoving)) {
        budget.moved.push(`web animation of ${properties.join(",")} on ${describe(this)}`);
      }
      return animate.call(this, keyframes, options);
    };
    // Springs driven from script rewrite an element's transform frame after frame.
    const styles = new MutationObserver((records) => {
      for (const record of records) {
        const element = record.target as HTMLElement;
        const transform = element.style?.transform;
        const values = budget.styleValues.get(element) ?? new Set<string>();
        if (!transform || values.size >= 3) {
          continue;
        }
        values.add(transform);
        budget.styleValues.set(element, values);
        if (values.size === 3) {
          budget.moved.push(`script-driven transform on ${describe(element)}`);
        }
      }
    });
    styles.observe(document, { subtree: true, attributes: true, attributeFilter: ["style"] });
    budget.stopWatchingMotion = () => {
      budget.watchesMotion = false;
      styles.disconnect();
    };
    // View transitions (React's <ViewTransition> calls this).
    const start = Document.prototype.startViewTransition;
    if (typeof start === "function") {
      Document.prototype.startViewTransition = function (this: Document, ...args: Parameters<typeof start>) {
        budget.viewTransitions += 1;
        return start.apply(this, args);
      };
    }
  }, MOVING_PROPERTIES);
}

export interface MotionBudgetReading {
  /** The slowest interaction, ms (0 without any). */
  inp: number;
  /** Which it was: event, target, page. */
  slowest: string;
  interactions: number;
  layoutShift: number;
  /** Each shift: its value, page and the elements that moved. */
  shifts: string[];
  moved: string[];
  viewTransitions: number;
  canvases: number;
}

/** What the current page recorded since it loaded. */
export function readMotionBudget(page: Page): Promise<MotionBudgetReading> {
  return page.evaluate(() => {
    const budget = window.__awBudget;
    const durations = Object.values(budget?.interactions ?? {});
    return {
      inp: durations.length > 0 ? Math.max(...durations) : 0,
      slowest: budget?.slowest ?? "",
      interactions: durations.length,
      layoutShift: budget?.layoutShift ?? 0,
      shifts: budget?.shifts ?? [],
      moved: budget?.moved ?? [],
      viewTransitions: budget?.viewTransitions ?? 0,
      canvases: document.querySelectorAll("canvas").length,
    };
  });
}

/**
 * Waits until the main thread has had no long task (over 50 ms) for
 * `quietMs` and then has nothing left to do at all (an idle callback
 * runs): the page has hydrated and rendered what it loaded, as a person
 * would see it before tapping on. The idle callback matters: React renders
 * a transition in slices of a few milliseconds, which are no long tasks,
 * yet the page is still at work until the last one has run.
 */
export async function waitForMainThreadQuiet(page: Page, { quietMs = 1000, timeoutMs = 60_000 } = {}): Promise<void> {
  await page.waitForFunction((quiet) => performance.now() - (window.__awBudget?.lastBusy ?? 0) > quiet, quietMs, {
    polling: 100,
    timeout: timeoutMs,
  });
  await page.evaluate(() => new Promise<void>((resolve) => requestIdleCallback(() => resolve())));
}

/**
 * From here on the interactions and layout shifts count; what moved since
 * the page loaded stays recorded. With `watchMotion: false` the motion
 * watch stops here (what moved until now stays): its observers run on the
 * page's own main thread, and a timed round should measure the page alone.
 */
export async function startMeasuring(page: Page, { watchMotion = true } = {}): Promise<void> {
  await page.evaluate((keepWatching) => {
    const budget = window.__awBudget;
    if (budget) {
      budget.interactions = {};
      budget.slowest = "";
      budget.layoutShift = 0;
      budget.shifts = [];
      if (!keepWatching) {
        budget.stopWatchingMotion();
      }
    }
  }, watchMotion);
}

/** A phone-class processor: Chromium runs the page `rate` times slower. */
export async function throttleCpu(page: Page, rate: number): Promise<void> {
  const session = await page.context().newCDPSession(page);
  await session.send("Emulation.setCPUThrottlingRate", { rate });
}
