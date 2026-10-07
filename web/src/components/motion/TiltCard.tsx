"use client";

/**
 * A card that tilts towards the mouse in 3D, with a soft glare where the
 * pointer is. Touch and pen input, and reduced motion, leave it flat.
 * Children can sit at different depths with <TiltLayer depth={24}>, which
 * makes them float above the card while it tilts.
 *
 *     <TiltCard className="rounded-2xl border …"><TiltLayer depth={30}>…</TiltLayer></TiltCard>
 */

import { useMotionTemplate, useMotionValue, useReducedMotion, useSpring } from "motion/react";
import * as m from "motion/react-m";
import type { PointerEvent, ReactNode } from "react";

import { SPRINGS, TILT_DEGREES } from "@/lib/motion";
import { tiltFromPointer } from "@/lib/motionMath";
import { cn } from "@/lib/cn";

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
  const reduced = useReducedMotion();
  const rotateX = useSpring(0, SPRINGS.bouncy);
  const rotateY = useSpring(0, SPRINGS.bouncy);
  const glareX = useMotionValue(50);
  const glareY = useMotionValue(50);
  const glareOpacity = useSpring(0, SPRINGS.snappy);
  const glareBackground = useMotionTemplate`radial-gradient(circle at ${glareX}% ${glareY}%, color-mix(in oklab, var(--accent-solid) 22%, transparent), transparent 60%)`;

  const onPointerMove = (event: PointerEvent<HTMLElement>) => {
    if (reduced || event.pointerType !== "mouse") {
      return;
    }
    const tilt = tiltFromPointer({ x: event.clientX, y: event.clientY }, event.currentTarget.getBoundingClientRect(), maxDegrees);
    rotateX.set(tilt.rotateX);
    rotateY.set(tilt.rotateY);
    glareX.set(tilt.glareX);
    glareY.set(tilt.glareY);
    glareOpacity.set(1);
  };
  const onPointerLeave = () => {
    rotateX.set(0);
    rotateY.set(0);
    glareOpacity.set(0);
  };

  const Element = as === "li" ? m.li : as === "figure" ? m.figure : m.div;
  return (
    <Element
      onPointerMove={onPointerMove}
      onPointerLeave={onPointerLeave}
      style={{ rotateX, rotateY, transformPerspective: 1000 }}
      className={cn("relative transform-3d", className)}
    >
      {children}
      {glare ? (
        <m.span
          aria-hidden
          className="pointer-events-none absolute inset-0 rounded-[inherit]"
          style={{ background: glareBackground, opacity: glareOpacity }}
        />
      ) : null}
    </Element>
  );
}

/** A layer of a TiltCard raised by `depth` px towards the viewer. */
export function TiltLayer({ depth, children, className }: { depth: number; children: ReactNode; className?: string }) {
  return (
    <div className={cn("transform-3d", className)} style={{ transform: `translateZ(${depth}px)` }}>
      {children}
    </div>
  );
}
