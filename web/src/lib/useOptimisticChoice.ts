"use client";

import { startTransition, useEffect, useRef, useState } from "react";

/**
 * Runs `task` once the browser has painted the next frame (a frame, then a
 * task after it); returns a function that cancels it.
 */
function afterNextPaint(task: () => void): () => void {
  let timer: number | undefined;
  const frame = window.requestAnimationFrame(() => {
    timer = window.setTimeout(task, 0);
  });
  return () => {
    window.cancelAnimationFrame(frame);
    window.clearTimeout(timer);
  };
}

/**
 * A choice (a period, an inbox view) that shows as chosen at once, while
 * what it changes follows after the browser has painted that: the tap
 * paints within one frame on a slow phone (the motion budget's 200 ms to
 * the next paint, e2e/motion-budget.spec.ts), then the page redraws in a
 * transition.
 *
 * The change waits for the paint rather than only going into a transition
 * because a choice usually writes the URL too (replaceUrlQuery): Next.js
 * applies a history change in a microtask, and inside a tap's event that
 * microtask renders the whole page at the event's urgent priority.
 *
 * Call it in the control's own small component, not in the page's: the
 * component that holds the shown value is what renders at once.
 */
export function useOptimisticChoice<Value>(value: Value, onChange: (next: Value) => void): [Value, (next: Value) => void] {
  const [chosen, setChosen] = useState<{ next: Value; from: Value } | null>(null);
  const cancelPending = useRef<(() => void) | null>(null);

  useEffect(() => () => cancelPending.current?.(), []);

  // The page caught up (or moved on): show what it says again. React's "previous props" pattern.
  if (chosen !== null && !Object.is(chosen.from, value)) {
    setChosen(null);
  }
  const shown = chosen !== null && Object.is(chosen.from, value) ? chosen.next : value;

  const choose = (next: Value) => {
    if (Object.is(next, shown)) {
      return;
    }
    setChosen({ next, from: value });
    cancelPending.current?.();
    cancelPending.current = afterNextPaint(() => {
      cancelPending.current = null;
      startTransition(() => onChange(next));
    });
  };
  return [shown, choose];
}
