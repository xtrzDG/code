"use client";

/**
 * Wraps a button or link that leans a few pixels towards the mouse and
 * springs back when it leaves: for the one main call to action of a page.
 * Touch, pen and reduced motion leave it still.
 *
 *     <MagneticButton><ButtonLink href="/login" size="lg">Get started</ButtonLink></MagneticButton>
 */

import { useSpring } from "motion/react";
import * as m from "motion/react-m";
import type { PointerEvent, ReactNode } from "react";

import { cn } from "@/lib/cn";
import { useHydrated } from "@/lib/csp/clientStyle";
import { SPRINGS } from "@/lib/motion";
import { magneticOffset } from "@/lib/motionMath";

import { useMotionPreference } from "./MotionPreference";

export function MagneticButton({
  children,
  strength = 0.25,
  maxOffset = 6,
  className,
}: {
  children: ReactNode;
  /** Share of the pointer's distance from the centre the button follows. */
  strength?: number;
  /** Largest shift in px. */
  maxOffset?: number;
  className?: string;
}) {
  const reduced = useMotionPreference().isCalm;
  const x = useSpring(0, SPRINGS.bouncy);
  const y = useSpring(0, SPRINGS.bouncy);
  // No style attribute in the server's HTML (the Content Security Policy refuses it).
  const hydrated = useHydrated();

  const onPointerMove = (event: PointerEvent<HTMLSpanElement>) => {
    if (reduced || event.pointerType !== "mouse") {
      return;
    }
    const offset = magneticOffset(
      { x: event.clientX, y: event.clientY },
      event.currentTarget.getBoundingClientRect(),
      strength,
      maxOffset,
    );
    x.set(offset.x);
    y.set(offset.y);
  };
  const onPointerLeave = () => {
    x.set(0);
    y.set(0);
  };

  return (
    <m.span
      className={cn("inline-flex", className)}
      style={hydrated ? { x, y } : undefined}
      onPointerMove={onPointerMove}
      onPointerLeave={onPointerLeave}
    >
      {children}
    </m.span>
  );
}
