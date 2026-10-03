"use client";

/**
 * The screens of the tunnel, moving with depth: going on, the screen
 * flies towards the viewer and fades while the next one comes out of the
 * distance (small, blurred, tipped back); going back, the other way round.
 * With reduced motion the screens only cross-fade (MotionConfig drops the
 * movement; the blur is left out here too).
 */

import { AnimatePresence, useReducedMotion, type Variants } from "motion/react";
import * as m from "motion/react-m";
import type { ReactNode } from "react";

import { EASINGS, springTransition } from "@/lib/motion";

/** 1: deeper, -1: back out. */
type Direction = 1 | -1 | 0;

function depthVariants(reduced: boolean): Variants {
  if (reduced) {
    return {
      enter: { opacity: 0 },
      center: { opacity: 1, transition: { duration: 0.2 } },
      exit: { opacity: 0, transition: { duration: 0.15 } },
    };
  }
  return {
    enter: (direction: Direction) => ({
      opacity: 0,
      scale: direction < 0 ? 1.12 : 0.82,
      z: direction < 0 ? 120 : -260,
      rotateX: direction < 0 ? -6 : 8,
      y: direction < 0 ? -24 : 36,
      filter: "blur(10px)",
    }),
    center: {
      opacity: 1,
      scale: 1,
      z: 0,
      rotateX: 0,
      y: 0,
      filter: "blur(0px)",
      transition: { ...springTransition("gentle"), opacity: { duration: 0.35 }, filter: { duration: 0.4 } },
      // A filter left on the screen would make it the containing block of fixed children.
      transitionEnd: { filter: "none" },
    },
    exit: (direction: Direction) => ({
      opacity: 0,
      scale: direction < 0 ? 0.86 : 1.16,
      z: direction < 0 ? -200 : 160,
      y: direction < 0 ? 24 : -18,
      filter: "blur(8px)",
      transition: { duration: 0.28, ease: [...EASINGS.exit] },
    }),
  };
}

export function TunnelStage({ placeKey, direction, children }: { placeKey: string; direction: Direction; children: ReactNode }) {
  const reduced = useReducedMotion() ?? false;
  return (
    <div className="tunnel-stage relative">
      <AnimatePresence mode="wait" custom={direction} initial={false}>
        <m.div
          key={placeKey}
          custom={direction}
          variants={depthVariants(reduced)}
          initial="enter"
          animate="center"
          exit="exit"
          style={{ transformStyle: "preserve-3d", transformOrigin: "50% 30%" }}
        >
          {children}
        </m.div>
      </AnimatePresence>
    </div>
  );
}
