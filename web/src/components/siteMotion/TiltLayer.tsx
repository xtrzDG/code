/** A layer of a <TiltCard> raised by `depth` px towards the viewer. */

import type { ReactNode } from "react";

import { cn } from "@/lib/cn";
import { tiltDepthClass, type TiltDepth } from "@/lib/motionClasses";

export function TiltLayer({ depth, children, className }: { depth: TiltDepth; children: ReactNode; className?: string }) {
  return (
    <div className={cn("transform-3d", tiltDepthClass(depth), className)}>
      {children}
    </div>
  );
}
