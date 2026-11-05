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

import type { ReactNode } from "react";

import { cn } from "@/lib/cn";
import { parallaxClass, type ParallaxSpeed } from "@/lib/motionClasses";

export function Parallax({
  speed,
  children,
  className,
}: {
  /** Positive: moves up faster than the page (nearer); negative: lags behind (further). */
  speed: ParallaxSpeed;
  children?: ReactNode;
  className?: string;
}) {
  return (
    <div aria-hidden className={cn("parallax-layer", parallaxClass(speed), className)}>
      {children}
    </div>
  );
}
