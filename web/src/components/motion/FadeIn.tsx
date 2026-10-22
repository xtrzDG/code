"use client";

/**
 * Content that arrives when it mounts, rising from below and, with
 * `depth`, from further back (the public site reveals on scroll in CSS:
 * `Reveal` in @/components/siteMotion).
 *
 *     <FadeIn tone="cabinet" delay={0.05}>…</FadeIn>
 *
 * It moves only when it comes into a page already in the browser: content
 * the server rendered is simply there (its hidden start would need a style
 * attribute, which the Content Security Policy refuses; see
 * useMountedAfterHydration). MotionProvider drops the movement under
 * reduced motion.
 */

import { useMountedAfterHydration } from "@/lib/csp/clientStyle";
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
  const enters = useMountedAfterHydration();
  if (!enters) {
    return <Element {...props}>{children}</Element>;
  }
  return (
    <Element initial="hidden" animate="visible" variants={revealVariants(tone, depth, delay)} {...props}>
      {children}
    </Element>
  );
}
