"use client";

/**
 * Content that rises in when it scrolls into view and, with `depth`, comes
 * from further back (smaller and tipped away):
 *
 *     <Reveal depth={1} amount={0.2}>…</Reveal>
 *
 * The movement is CSS (src/styles/siteMotion.css, the `gentle` spring);
 * this component only marks the element `data-revealed` once it is seen.
 * Server and browser render the same hidden start, so hydration matches;
 * reduced motion makes it appear at once, and the landing page's <noscript>
 * style shows every `data-reveal` element when scripts never run.
 */

import { useEffect, useRef, type RefObject } from "react";

import type { MotionBlockProps } from "@/components/motion/elements";

import { onceInView } from "./inView";
import { revealStyle } from "./revealStyle";

export interface RevealProps extends MotionBlockProps {
  /** 0 = rise only; 1 = also come from further back (scale, tilt). */
  depth?: number;
  /** Seconds after it is seen. */
  delay?: number;
  /** Share of the element that must be visible before it reveals. */
  amount?: number;
}

export function Reveal({ as = "div", depth = 0, delay = 0, amount = 0.25, style, children, ...props }: RevealProps) {
  const ref = useRef<HTMLElement>(null);
  useEffect(() => {
    const element = ref.current;
    return element ? onceInView(element, amount, () => element.setAttribute("data-revealed", "")) : undefined;
  }, [amount]);
  // Every tag takes the same attributes here; one element type keeps the ref simple.
  const Element = as as "div";
  return (
    <Element ref={ref as RefObject<HTMLDivElement>} data-reveal="" style={revealStyle(depth, delay, style)} {...props}>
      {children}
    </Element>
  );
}
