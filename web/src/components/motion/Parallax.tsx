"use client";

/**
 * A depth layer: it drifts against the scroll while its block crosses the
 * screen, so layers with different `speed`s seem to sit at different
 * distances (backgrounds slow, foregrounds fast). Reduced motion keeps it
 * still. It starts unshifted on the server and in the browser alike, and
 * only scrolling moves it, so hydration always matches.
 *
 *     <Parallax speed={-0.3} className="absolute inset-0">…glow…</Parallax>
 */

import { useMotionValue, useReducedMotion, useScroll } from "motion/react";
import * as m from "motion/react-m";
import { useEffect, useRef, type ReactNode } from "react";

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
  const ref = useRef<HTMLDivElement>(null);
  const reduced = useReducedMotion();
  const { scrollYProgress } = useScroll({ target: ref, offset: ["start end", "end start"] });
  const y = useMotionValue(0);

  useEffect(() => {
    if (reduced) {
      y.set(0);
      return;
    }
    // 0 when the block is in the middle of the screen.
    const update = (progress: number) => y.set((0.5 - progress) * 2 * speed * DRIFT_PX);
    update(scrollYProgress.get());
    return scrollYProgress.on("change", update);
  }, [reduced, scrollYProgress, speed, y]);

  return (
    <m.div ref={ref} aria-hidden className={className} style={{ y }}>
      {children}
    </m.div>
  );
}
