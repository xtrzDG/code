/**
 * One item of a <Stagger> group: it waits for the group and arrives in its
 * turn, from further back with `depth`. Plain markup with no script of
 * its own: from a server component it is HTML alone.
 */

import type { MotionBlockProps } from "@/components/motion/elements";

import { revealStyle } from "./revealStyle";

export function StaggerItem({ as = "div", depth = 0, style, children, ...props }: MotionBlockProps & { depth?: number }) {
  const Element = as;
  return (
    <Element data-reveal="" data-reveal-item="" style={revealStyle(depth, 0, style)} {...props}>
      {children}
    </Element>
  );
}
