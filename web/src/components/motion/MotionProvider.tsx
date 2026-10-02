"use client";

/**
 * Motion for the whole site, mounted once by the root layout.
 *
 * - LazyMotion: the `m.*` elements ship without their animation code, which
 *   loads right after the page (`motionFeatures.ts`, domMax: gestures,
 *   in-view, layout and shared-layout animations). `strict` makes a stray
 *   `motion.div` (the heavy, all-inclusive element) throw: use `m.div`.
 * - MotionConfig reducedMotion="user": with `prefers-reduced-motion` every
 *   transform and layout animation jumps to its end and fades stay short.
 */

import { LazyMotion, MotionConfig } from "motion/react";
import type { ReactNode } from "react";

const loadFeatures = () => import("./motionFeatures").then((module) => module.default);

export function MotionProvider({ children }: { children: ReactNode }) {
  return (
    <LazyMotion features={loadFeatures} strict>
      <MotionConfig reducedMotion="user">{children}</MotionConfig>
    </LazyMotion>
  );
}
