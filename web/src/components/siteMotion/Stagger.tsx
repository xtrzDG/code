"use client";

/**
 * A group whose items (<StaggerItem>) arrive one after another, `step`
 * seconds apart, when the group scrolls into view:
 *
 *     <Stagger as="ul" className="grid gap-4 md:grid-cols-3">
 *       {steps.map((step) => <StaggerItem as="li" key={step.id}>…</StaggerItem>)}
 *     </Stagger>
 *
 * Once seen, the group numbers its own items (`--reveal-index`, which their
 * CSS delay multiplies) and is marked `data-revealed`; the rest is CSS
 * (src/styles/siteMotion.css).
 */

import { useEffect, useRef, type CSSProperties, type RefObject } from "react";

import type { MotionBlockProps } from "@/components/motion/elements";
import { STAGGER } from "@/lib/motion";

import { onceInView } from "./inView";

/** Numbers the group's own items (not those of a group inside it) and shows them. */
function revealGroup(group: HTMLElement): void {
  const items = [...group.querySelectorAll<HTMLElement>("[data-reveal-item]")].filter(
    (item) => item.parentElement?.closest("[data-reveal-group]") === group,
  );
  items.forEach((item, index) => item.style.setProperty("--reveal-index", String(index)));
  group.setAttribute("data-revealed", "");
}

export function Stagger({
  as = "div",
  delay = 0,
  step = STAGGER.landing,
  amount = 0.15,
  style,
  children,
  ...props
}: MotionBlockProps & {
  /** Seconds before the first item. */
  delay?: number;
  /** Seconds between two items. */
  step?: number;
  /** Share of the group that must be visible before it starts. */
  amount?: number;
}) {
  const ref = useRef<HTMLElement>(null);
  useEffect(() => {
    const group = ref.current;
    return group ? onceInView(group, amount, () => revealGroup(group)) : undefined;
  }, [amount]);
  const timing = { "--stagger-delay": `${delay}s`, "--stagger-step": `${step}s` } as CSSProperties;
  const Element = as as "div";
  return (
    <Element ref={ref as RefObject<HTMLDivElement>} data-reveal-group="" style={{ ...timing, ...style }} {...props}>
      {children}
    </Element>
  );
}
