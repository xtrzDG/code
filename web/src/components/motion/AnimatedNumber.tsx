"use client";

/**
 * A number that counts up to its value when it first comes into view, and
 * from the old value to the new one when it changes (a new period on the
 * dashboard). The markup always holds the final text, so the server, screen
 * readers and reduced motion (the device's or the cabinet's own) see the
 * real number; the counting only rewrites the text node in animation
 * frames, without React renders. With `countIn={false}` the first value
 * simply shows and only later changes count (a badge: 3 → 4).
 *
 * The count never moves the text around it (no layout shift, CLS 0): it
 * runs inside the final number's width, so the layout changes once, when
 * the value does, as it would without the count. A number that would have
 * to start wider than it ends (16 → 4) does not count; it changes at once,
 * and so does one that changes while it is not shown at all.
 *
 *     <AnimatedNumber value={stats.conversations} format={(n) => numberFormat.format(n)} />
 */

import { useEffect, useLayoutEffect, useRef } from "react";

import { cn } from "@/lib/cn";
import { countUpValue, fractionDigitsOf } from "@/lib/motionMath";
import { prefersCalmMotion } from "@/lib/motionPreference";

const DEFAULT_DURATION_MS = 900;

/** Rounding of the browser's widths: a smaller difference is no change. */
const WIDTH_TOLERANCE_PX = 0.5;

/** Whether the span is laid out at all (display: none on it or an ancestor leaves it without a box). */
function hasBox(node: HTMLElement): boolean {
  return node.getClientRects().length > 0;
}

/**
 * Holds the span at `width` (the final number's) while the count runs; null
 * lets it size itself again. The digits stay at the start of the box (the
 * start a parent's centring or end alignment would otherwise move as the
 * text grows): a text whose start moves is a layout shift, even inside a
 * box that keeps still.
 */
function holdWidth(node: HTMLElement, width: number | null): void {
  if (width === null) {
    node.style.removeProperty("width");
    node.style.removeProperty("text-align");
    return;
  }
  node.style.width = `${width}px`;
  node.style.textAlign = "start";
}

export function AnimatedNumber({
  value,
  format,
  durationMs = DEFAULT_DURATION_MS,
  countIn = true,
  className,
}: {
  value: number;
  format: (value: number) => string;
  durationMs?: number;
  /** Count up from 0 the first time (false: show the first value as it is). */
  countIn?: boolean;
  className?: string;
}) {
  const element = useRef<HTMLSpanElement>(null);
  /** The value on screen now (null before the first count). */
  const shown = useRef<number | null>(countIn ? null : value);
  const formatRef = useRef(format);
  useEffect(() => {
    formatRef.current = format;
  });

  // Before paint: the first frame already shows the start value, never a flash of the final one.
  useLayoutEffect(() => {
    const node = element.current;
    if (!node) {
      return;
    }
    const from = shown.current ?? 0;
    // Only a new text touches the page (the count repeats a value over several frames), and in
    // React's own text node, which then keeps showing what React renders later.
    const write = (current: number) => {
      const text = formatRef.current(current);
      const only = node.firstChild;
      if (only instanceof Text && only === node.lastChild) {
        if (only.data !== text) {
          only.data = text;
        }
      } else if (node.textContent !== text) {
        node.textContent = text;
      }
    };
    const settle = () => {
      shown.current = value;
      holdWidth(node, null);
      write(value);
    };
    const cannotCount = typeof IntersectionObserver === "undefined" || !Number.isFinite(from) || !Number.isFinite(value);
    // A number without a box (in a closed fold, a hidden sheet, the phone's sidebar) has no width to
    // count in, and nobody saw the old value: it shows the new one, and appears with it.
    if (from === value || cannotCount || prefersCalmMotion() || !hasBox(node)) {
      settle();
      return;
    }
    // The final number's width holds the count; a start wider than that would push the text after it.
    holdWidth(node, null);
    write(value);
    const finalWidth = node.getBoundingClientRect().width;
    write(from);
    if (node.getBoundingClientRect().width > finalWidth + WIDTH_TOLERANCE_PX) {
      settle();
      return;
    }
    holdWidth(node, finalWidth);
    const digits = fractionDigitsOf(value);
    let frame = 0;
    let started: number | null = null;
    const tick = (now: number) => {
      started ??= now;
      const current = countUpValue(from, value, now - started, durationMs, digits);
      shown.current = current;
      write(current);
      if (current === value) {
        holdWidth(node, null);
      } else {
        frame = window.requestAnimationFrame(tick);
      }
    };
    // Count only once the number can be seen.
    const observer = new IntersectionObserver((entries) => {
      if (entries.some((entry) => entry.isIntersecting)) {
        observer.disconnect();
        frame = window.requestAnimationFrame(tick);
      }
    });
    observer.observe(node);
    // A new value counts on from what is on screen now (shown), not from the old target.
    return () => {
      observer.disconnect();
      window.cancelAnimationFrame(frame);
    };
  }, [value, durationMs]);

  return (
    <span ref={element} className={cn("inline-block whitespace-nowrap tabular-nums", className)}>
      {format(value)}
    </span>
  );
}
