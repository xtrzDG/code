/**
 * One item of a <Stagger> group: it waits for the group and arrives in its
 * turn, from further back with `depth`. Plain markup with no script of
 * its own: from a server component it is HTML alone.
 */

import type { MotionBlockProps } from "@/components/motion/elements";
import { cn } from "@/lib/cn";
import { revealClasses, type RevealDepth } from "@/lib/motionClasses";

export function StaggerItem({
  as = "div",
  depth = 0,
  className,
  children,
  ...props
}: MotionBlockProps & { depth?: RevealDepth }) {
  const Element = as;
  return (
    <Element data-reveal="" data-reveal-item="" className={cn(revealClasses(depth, 0), className) || undefined} {...props}>
      {children}
    </Element>
  );
}
