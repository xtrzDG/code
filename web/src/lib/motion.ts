/**
 * Motion tokens: the durations, easings, springs, distances and staggers
 * every animation of the site uses, for motion (JavaScript, `motion/react`)
 * and for CSS (globals.css declares the same values as custom properties;
 * `cssMotionTokens()` lists them and a unit test keeps the two in step).
 *
 * The cabinet moves little and quickly (`cabinet` distances, `snappy`
 * springs); the landing page is expressive (`landing`, `gentle`, `bouncy`).
 * Reduced motion: <MotionProvider> (MotionConfig reducedMotion="user") turns
 * every transform and layout animation off and keeps short fades; the CSS
 * side stops in globals.css under `prefers-reduced-motion`.
 */

import type { Transition, Variants } from "motion/react";

import { cubicBezierCss, springToCssLinear, type SpringToken } from "./motionMath";

/** Seconds (motion's unit); CSS gets the same in milliseconds. */
export const DURATIONS = {
  instant: 0.1,
  fast: 0.15,
  base: 0.24,
  slow: 0.42,
  reveal: 0.7,
} as const;

export type DurationName = keyof typeof DURATIONS;

type Bezier = readonly [number, number, number, number];

export const EASINGS = {
  /** Most transitions: quick start, soft landing. */
  standard: [0.2, 0.8, 0.2, 1],
  /** Things arriving from far (pages, reveals): a long, calm tail. */
  emphasized: [0.16, 1, 0.3, 1],
  /** Things leaving: accelerate away. */
  exit: [0.4, 0, 1, 1],
} as const satisfies Record<string, Bezier>;

export type EasingName = keyof typeof EASINGS;

export const SPRINGS = {
  /** A pressed button: firm, with a little bounce back. */
  press: { stiffness: 700, damping: 30, mass: 1 },
  /** Dialogs, toasts, menus: fast, barely overshooting. */
  snappy: { stiffness: 520, damping: 34, mass: 1 },
  /** The sidebar's active marker and lists making room. */
  layout: { stiffness: 500, damping: 40, mass: 1 },
  /** Landing reveals: no overshoot, unhurried. */
  gentle: { stiffness: 170, damping: 26, mass: 1 },
  /** Landing play (tilt, magnetic buttons): lively. */
  bouncy: { stiffness: 300, damping: 18, mass: 1 },
} as const satisfies Record<string, SpringToken>;

export type SpringName = keyof typeof SPRINGS;

/** How far content rises when it appears (px). */
export const DISTANCES = { cabinet: 8, landing: 28 } as const;

/** Delay between siblings appearing one after another (seconds). */
export const STAGGER = { cabinet: 0.035, landing: 0.08 } as const;

/** Largest tilt of a TiltCard at its edge (degrees). */
export const TILT_DEGREES = { subtle: 4, expressive: 9 } as const;

export function springTransition(name: SpringName, delay = 0): Transition {
  return { type: "spring", ...SPRINGS[name], delay };
}

export function tweenTransition(duration: DurationName, easing: EasingName = "standard", delay = 0): Transition {
  return { type: "tween", duration: DURATIONS[duration], ease: [...EASINGS[easing]], delay };
}

export type MotionTone = keyof typeof DISTANCES;

/**
 * Content arriving: from below (`distance` px) and, with `depth` > 0, from
 * further back (smaller and tipped away), as if it came out of the page;
 * `delay` (seconds) holds it back behind its neighbours.
 * The same on the server and in the browser (no reduced-motion branch here:
 * MotionConfig drops the movement and keeps the fade).
 */
export function revealVariants(tone: MotionTone, depth = 0, delay = 0): Variants {
  const landing = tone === "landing";
  return {
    hidden: {
      opacity: 0,
      y: DISTANCES[tone],
      scale: 1 - depth * 0.04,
      rotateX: depth * 8,
    },
    visible: {
      opacity: 1,
      y: 0,
      scale: 1,
      rotateX: 0,
      transition: landing ? springTransition("gentle", delay) : tweenTransition("base", "emphasized", delay),
    },
  };
}

/** A parent revealing its children one after another (`StaggerItem`s). */
export function staggerVariants(tone: MotionTone, delayChildren = 0): Variants {
  return {
    hidden: {},
    visible: { transition: { staggerChildren: STAGGER[tone], delayChildren } },
  };
}

/**
 * Custom properties globals.css must declare, with their values: durations
 * in ms, easings as `cubic-bezier()`, springs as `linear()` plus the
 * duration a CSS transition needs to play the whole spring.
 */
export function cssMotionTokens(): Record<string, string> {
  const tokens: Record<string, string> = {};
  for (const [name, seconds] of Object.entries(DURATIONS)) {
    tokens[`--motion-${name}`] = `${Math.round(seconds * 1000)}ms`;
  }
  for (const [name, points] of Object.entries(EASINGS)) {
    tokens[`--ease-${name}`] = cubicBezierCss(points);
  }
  for (const name of ["press", "snappy"] as const) {
    const { easing, durationMs } = springToCssLinear(SPRINGS[name]);
    tokens[`--ease-spring-${name}`] = easing;
    tokens[`--motion-spring-${name}`] = `${durationMs}ms`;
  }
  return tokens;
}
