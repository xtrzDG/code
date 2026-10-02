"use client";

/**
 * Content that arrives: on mount (FadeIn) or when it scrolls into view
 * (Reveal), rising from below and, with `depth`, from further back.
 *
 *     <Reveal depth={1}><PlanCard … /></Reveal>
 *     <FadeIn tone="cabinet" delay={0.05}>…</FadeIn>
 *
 * Server and browser render the same hidden start (no reduced-motion branch
 * in the markup, so hydration matches); MotionProvider drops the movement
 * under reduced motion. `data-reveal` lets a <noscript> style show the
 * content when scripts never run (see the landing page).
 */

import { revealVariants, type MotionTone } from "@/lib/motion";

import { MOTION_ELEMENTS, type MotionBlockProps } from "./elements";

export interface RevealProps extends MotionBlockProps {
  tone?: MotionTone;
  /** 0 = rise only; 1 = also come from further back (scale, tilt). */
  depth?: number;
  /** Seconds after the trigger. */
  delay?: number;
  /** Share of the element that must be visible before it reveals. */
  amount?: number;
}

export function Reveal({ as = "div", tone = "landing", depth = 0, delay = 0, amount = 0.25, children, ...props }: RevealProps) {
  const Element = MOTION_ELEMENTS[as];
  return (
    <Element
      data-reveal=""
      initial="hidden"
      whileInView="visible"
      // Once: content that has arrived stays, scrolling back up does not hide it again.
      viewport={{ once: true, amount }}
      variants={revealVariants(tone, depth, delay)}
      {...props}
    >
      {children}
    </Element>
  );
}

export function FadeIn({ as = "div", tone = "cabinet", depth = 0, delay = 0, children, ...props }: Omit<RevealProps, "amount">) {
  const Element = MOTION_ELEMENTS[as];
  return (
    <Element data-reveal="" initial="hidden" animate="visible" variants={revealVariants(tone, depth, delay)} {...props}>
      {children}
    </Element>
  );
}
