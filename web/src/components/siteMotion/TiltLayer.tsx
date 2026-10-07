/** A layer of a <TiltCard> raised by `depth` px towards the viewer. */

import type { ReactNode } from "react";

import { cn } from "@/lib/cn";

export function TiltLayer({ depth, children, className }: { depth: number; children: ReactNode; className?: string }) {
  return (
    <div className={cn("transform-3d", className)} style={{ transform: `translateZ(${depth}px)` }}>
      {children}
    </div>
  );
}
