"use client";

/**
 * A group whose items arrive one after another when the group scrolls into
 * view (or at once on mount with `onMount`).
 *
 *     <Stagger as="ul" className="grid gap-4 md:grid-cols-3">
 *       {steps.map((step) => <StaggerItem as="li" key={step.id}>…</StaggerItem>)}
 *     </Stagger>
 *
 * Items take their timing from the group; give them `depth` to come from
 * further back.
 */

import { revealVariants, staggerVariants, type MotionTone } from "@/lib/motion";

import { MOTION_ELEMENTS, type MotionBlockProps } from "./elements";

export function Stagger({
  as = "div",
  tone = "landing",
  delay = 0,
  step,
  amount = 0.15,
  onMount = false,
  children,
  ...props
}: MotionBlockProps & {
  tone?: MotionTone;
  delay?: number;
  /** Seconds between two items (the tone's own step unless given). */
  step?: number;
  amount?: number;
  onMount?: boolean;
}) {
  const Element = MOTION_ELEMENTS[as];
  const trigger = onMount ? { animate: "visible" } : { whileInView: "visible", viewport: { once: true, amount } };
  return (
    <Element initial="hidden" variants={staggerVariants(tone, delay, step)} {...trigger} {...props}>
      {children}
    </Element>
  );
}

export function StaggerItem({
  as = "div",
  tone = "landing",
  depth = 0,
  children,
  ...props
}: MotionBlockProps & { tone?: MotionTone; depth?: number }) {
  const Element = MOTION_ELEMENTS[as];
  return (
    <Element data-reveal="" variants={revealVariants(tone, depth)} {...props}>
      {children}
    </Element>
  );
}
