/**
 * A page rising into place when it is opened. Used by the route templates
 * (`template.tsx`), which React remounts on every navigation between their
 * child segments, so the animation plays once per page.
 *
 * Pure CSS (`animate-page-in`, src/styles/motion.css): it starts with the
 * first paint, before any script, and leaves no transform behind when it
 * ends (fixed and sticky children keep their place). Server-safe.
 */

import type { ReactNode } from "react";

import { cn } from "@/lib/cn";

export function PageTransition({ children, className }: { children: ReactNode; className?: string }) {
  return <div className={cn("animate-page-in", className)}>{children}</div>;
}
