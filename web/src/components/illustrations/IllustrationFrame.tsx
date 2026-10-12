/**
 * The canvas every spot illustration draws on: a 160 × 120 SVG that fills
 * its box's width, hidden from screen readers (the words beside it carry
 * the meaning). Server-safe: no state, no script.
 *
 * The art is drawn with the theme's tokens only, as Tailwind fill and
 * stroke utilities (`fill-surface`, `stroke-line-strong`, `fill-accent-solid`,
 * `fill-tone-sand`…), so it follows the light and the dark theme by itself
 * and never leaves the palette. Small parts move gently (`aw-float`,
 * `aw-drift`, `aw-twinkle`, `aw-beat`: src/styles/illustrations.css) and
 * keep still with reduced motion.
 */

import type { ReactNode } from "react";

import { cn } from "@/lib/cn";

export interface IllustrationProps {
  className?: string;
}

export function IllustrationFrame({ name, className, children }: { name: string; className?: string; children: ReactNode }) {
  return (
    <svg
      viewBox="0 0 160 120"
      aria-hidden
      focusable="false"
      data-illustration={name}
      className={cn("aw-illustration h-auto w-full", className)}
    >
      {children}
    </svg>
  );
}

/** A four-pointed glint, centred on (x, y). */
export function Sparkle({ x, y, size = 4, className }: { x: number; y: number; size?: number; className?: string }) {
  const s = size;
  return (
    <path
      d={`M${x} ${y - s}Q${x + s * 0.18} ${y - s * 0.18} ${x + s} ${y}Q${x + s * 0.18} ${y + s * 0.18} ${x} ${y + s}Q${x - s * 0.18} ${y + s * 0.18} ${x - s} ${y}Q${x - s * 0.18} ${y - s * 0.18} ${x} ${y - s}Z`}
      className={cn("aw-twinkle fill-tone-sand", className)}
    />
  );
}

/** The soft shadow the drawing stands on. */
export function Ground({ width = 92 }: { width?: number }) {
  return <ellipse cx="80" cy="110" rx={width / 2} ry="4.5" className="fill-line" />;
}
