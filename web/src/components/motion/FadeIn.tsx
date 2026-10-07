"use client";

/**
 * Content that arrives when it mounts, rising from below and, with
 * `depth`, from further back (the public site reveals on scroll in CSS:
 * `Reveal` in @/components/siteMotion).
 *
 *     <FadeIn tone="cabinet" delay={0.05}>…</FadeIn>
 *
 * Server and browser render the same hidden start (no reduced-motion branch
 * in the markup, so hydration matches); MotionProvider drops the movement
 * under reduced motion. `data-reveal` lets a <noscript> style show the
 * content when scripts never run (see the landing page).
 */

import { revealVariants, type MotionTone } from "@/lib/motion";

import { MOTION_ELEMENTS, type MotionBlockProps } from "./elements";

interface FadeInProps extends MotionBlockProps {
  tone?: MotionTone;
  /** 0 = rise only; 1 = also come from further back (scale, tilt). */
  depth?: number;
  /** Seconds after mounting. */
  delay?: number;
}

export function FadeIn({ as = "div", tone = "cabinet", depth = 0, delay = 0, children, ...props }: FadeInProps) {
  const Element = MOTION_ELEMENTS[as];
  return (
    <Element data-reveal="" initial="hidden" animate="visible" variants={revealVariants(tone, depth, delay)} {...props}>
      {children}
    </Element>
  );
}
