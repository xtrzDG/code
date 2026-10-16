/**
 * A depth layer: it drifts against the scroll while its block crosses the
 * screen, so layers with different `speed`s seem to sit at different
 * distances (backgrounds slow, foregrounds fast).
 *
 *     <Parallax speed={-0.3} className="absolute inset-0">…glow…</Parallax>
 *
 * A CSS scroll-driven animation (animation-timeline: view(), in
 * src/styles/siteMotion.css) moves it, without any script; browsers without
 * scroll timelines, and reduced motion, keep it still.
 */

import type { CSSProperties, ReactNode } from "react";

import { cn } from "@/lib/cn";

/** px of drift per unit of `speed` over the block's whole way across the screen. */
const DRIFT_PX = 120;

export function Parallax({
  speed,
  children,
  className,
}: {
  /** Positive: moves up faster than the page (nearer); negative: lags behind (further). */
  speed: number;
  children?: ReactNode;
  className?: string;
}) {
  const shift = { "--parallax-shift": `${speed * DRIFT_PX}px` } as CSSProperties;
  return (
    <div aria-hidden className={cn("parallax-layer", className)} style={shift}>
      {children}
    </div>
  );
}
