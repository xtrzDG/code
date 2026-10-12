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
 *     <AnimatedNumber value={stats.conversations} format={(n) => numberFormat.format(n)} />
 */

import { useEffect, useLayoutEffect, useRef } from "react";

import { cn } from "@/lib/cn";
import { countUpValue, fractionDigitsOf } from "@/lib/motionMath";
import { prefersCalmMotion } from "@/lib/motionPreference";

const DEFAULT_DURATION_MS = 900;

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
    const write = (current: number) => {
      node.textContent = formatRef.current(current);
    };
    const cannotCount = typeof IntersectionObserver === "undefined" || !Number.isFinite(from) || !Number.isFinite(value);
    if (from === value || cannotCount || prefersCalmMotion()) {
      shown.current = value;
      write(value);
      return;
    }
    write(from);
    const digits = fractionDigitsOf(value);
    let frame = 0;
    let started: number | null = null;
    const tick = (now: number) => {
      started ??= now;
      const current = countUpValue(from, value, now - started, durationMs, digits);
      shown.current = current;
      write(current);
      if (current !== value) {
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
    <span ref={element} className={cn("tabular-nums", className)}>
      {format(value)}
    </span>
  );
}
