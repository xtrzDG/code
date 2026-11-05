"use client";

/**
 * Wraps the one main call to action of a page: it leans a few pixels
 * towards the mouse and springs back when the mouse leaves. Touch, pen and
 * reduced motion leave it still.
 *
 *     <MagneticButton><ButtonLink href="/create" size="lg">Get started</ButtonLink></MagneticButton>
 *
 * The pointer writes --magnet-x and --magnet-y; CSS moves the button with
 * the `bouncy` spring (src/styles/siteMotion.css).
 */

import type { PointerEvent, ReactNode } from "react";

import { cn } from "@/lib/cn";
import { magneticOffset } from "@/lib/motionMath";

/** Leans the wrapper towards the mouse by `strength` of its distance from the centre, at most `maxOffset` px. */
function leanTowards(event: PointerEvent<HTMLElement>, strength: number, maxOffset: number): void {
  if (event.pointerType !== "mouse") {
    return;
  }
  const wrapper = event.currentTarget;
  const offset = magneticOffset({ x: event.clientX, y: event.clientY }, wrapper.getBoundingClientRect(), strength, maxOffset);
  wrapper.style.setProperty("--magnet-x", `${offset.x}px`);
  wrapper.style.setProperty("--magnet-y", `${offset.y}px`);
}

/** Lets the wrapper spring back to its place. */
function release(event: PointerEvent<HTMLElement>): void {
  event.currentTarget.style.removeProperty("--magnet-x");
  event.currentTarget.style.removeProperty("--magnet-y");
}

export function MagneticButton({
  children,
  strength = 0.25,
  maxOffset = 6,
  className,
}: {
  children: ReactNode;
  /** Share of the pointer's distance from the centre the button follows. */
  strength?: number;
  /** Largest shift in px. */
  maxOffset?: number;
  className?: string;
}) {
  return (
    <span
      className={cn("magnetic inline-flex", className)}
      onPointerMove={(event) => leanTowards(event, strength, maxOffset)}
      onPointerLeave={release}
    >
      {children}
    </span>
  );
}
