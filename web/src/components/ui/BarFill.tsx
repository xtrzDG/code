"use client";

/**
 * The filled part of a bar or meter: `percent` of its track wide.
 *
 *     <div className="h-2 overflow-hidden rounded-full bg-surface-muted">
 *       <BarFill percent={42} className="h-full rounded-full bg-accent-solid" />
 *     </div>
 *
 * The width is set through the CSSOM: the Content Security Policy refuses
 * a style attribute in the server's HTML, so a bar the server renders
 * starts empty and fills once the page has hydrated (with the bar's own
 * width transition, if it has one); a bar first drawn in the browser is
 * full at once.
 */

import type { ReactNode } from "react";

import { cn } from "@/lib/cn";
import { useClientStyle } from "@/lib/csp/clientStyle";

export function BarFill({
  percent,
  className,
  as = "div",
  children,
}: {
  /** 0–100; values outside are clamped. */
  percent: number;
  className?: string;
  as?: "div" | "span";
  /** Decoration inside the fill (a glint). */
  children?: ReactNode;
}) {
  const style = useClientStyle({ width: `${Math.min(100, Math.max(0, percent))}%` });
  const Element = as;
  return (
    <Element aria-hidden className={cn("w-0", className)} style={style}>
      {children}
    </Element>
  );
}
