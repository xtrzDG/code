"use client";

/**
 * A small burst of sparks from the middle of its box, for a moment worth
 * celebrating (a milestone's toast, the phone check that worked). It plays
 * once on mount and takes no room (absolutely placed in a relative
 * parent). Nothing moves with reduced motion: the moment's text carries it.
 *
 *     <div className="relative"><Burst /> …</div>
 */

import { useReducedMotion } from "motion/react";
import * as m from "motion/react-m";

import { tweenTransition } from "@/lib/motion";
import { burstSparks } from "@/lib/motionMath";

/** Accent, success and warm tones of the theme (decoration only). */
const SPARK_CLASSES = ["bg-accent", "bg-success", "bg-warning", "bg-accent-solid"] as const;

export function Burst({ count = 14, radius = 56 }: { count?: number; radius?: number }) {
  const isReduced = useReducedMotion();
  if (isReduced) {
    return null;
  }
  return (
    <span aria-hidden className="pointer-events-none absolute inset-0 flex items-center justify-center">
      {burstSparks(count, radius).map((spark, index) => (
        <m.span
          key={index}
          className={`absolute size-1.5 rounded-full ${SPARK_CLASSES[index % SPARK_CLASSES.length]}`}
          initial={{ x: 0, y: 0, opacity: 1, scale: 1 }}
          animate={{ x: spark.x, y: spark.y, opacity: 0, scale: 0.4 }}
          transition={tweenTransition("reveal", "emphasized", spark.delay)}
        />
      ))}
    </span>
  );
}
