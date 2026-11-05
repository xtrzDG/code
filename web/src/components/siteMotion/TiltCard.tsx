"use client";

/**
 * A card that tilts towards the mouse in 3D, with a soft glare where the
 * pointer is; touch, pen and reduced motion leave it flat. Children can
 * float above it at different depths with <TiltLayer depth={24}>.
 *
 *     <TiltCard className="rounded-2xl border …"><TiltLayer depth={30}>…</TiltLayer></TiltCard>
 *
 * The pointer only writes custom properties (--tilt-x, --tilt-y, --glare-x,
 * --glare-y); CSS turns the card with the `bouncy` spring
 * (src/styles/siteMotion.css), without a React render per move.
 */

import type { PointerEvent, ReactNode } from "react";

import { TILT_DEGREES } from "@/lib/motion";
import { tiltFromPointer } from "@/lib/motionMath";
import { cn } from "@/lib/cn";

/** Points the card at the mouse; any other pointer leaves it as it is. */
function tiltTowards(event: PointerEvent<HTMLElement>, maxDegrees: number): void {
  if (event.pointerType !== "mouse") {
    return;
  }
  const card = event.currentTarget;
  const tilt = tiltFromPointer({ x: event.clientX, y: event.clientY }, card.getBoundingClientRect(), maxDegrees);
  card.style.setProperty("--tilt-x", `${tilt.rotateX}deg`);
  card.style.setProperty("--tilt-y", `${tilt.rotateY}deg`);
  card.style.setProperty("--glare-x", `${tilt.glareX}%`);
  card.style.setProperty("--glare-y", `${tilt.glareY}%`);
  card.setAttribute("data-tilting", "");
}

/** Lets the card spring back flat. */
function settle(event: PointerEvent<HTMLElement>): void {
  const card = event.currentTarget;
  card.style.removeProperty("--tilt-x");
  card.style.removeProperty("--tilt-y");
  card.removeAttribute("data-tilting");
}

export function TiltCard({
  children,
  className,
  maxDegrees = TILT_DEGREES.expressive,
  glare = true,
  as = "div",
}: {
  children: ReactNode;
  className?: string;
  maxDegrees?: number;
  glare?: boolean;
  as?: "div" | "li" | "figure";
}) {
  const Element = as as "div";
  return (
    <Element
      onPointerMove={(event) => tiltTowards(event, maxDegrees)}
      onPointerLeave={settle}
      className={cn("tilt-card relative transform-3d", className)}
    >
      {children}
      {glare ? <span aria-hidden className="tilt-glare" /> : null}
    </Element>
  );
}
