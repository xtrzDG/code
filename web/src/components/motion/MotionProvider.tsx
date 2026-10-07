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
 *
 * The public site moves in CSS alone (src/components/siteMotion; a policy
 * test keeps `motion/react` out of its pages), so there `animates` is false
 * and the animation code is not even fetched. The toast list brings its own.
 */

import { LazyMotion, MotionConfig } from "motion/react";
import type { ReactNode } from "react";

const loadFeatures = () => import("./motionFeatures").then((module) => module.default);

export function MotionProvider({ animates = true, children }: { animates?: boolean; children: ReactNode }) {
  const config = <MotionConfig reducedMotion="user">{children}</MotionConfig>;
  return animates ? (
    <LazyMotion features={loadFeatures} strict>
      {config}
    </LazyMotion>
  ) : (
    config
  );
}
