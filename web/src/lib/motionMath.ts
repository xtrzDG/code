/**
 * The arithmetic behind the cabinet's motion: springs (for JavaScript
 * animations and, sampled into CSS `linear()` easings, for CSS ones), a card
 * tilting towards the pointer, a button drawn to it, numbers counting up and
 * frame-rate independent smoothing. Pure functions, no DOM.
 */

/** A physical spring: how hard it pulls, how much it is slowed down, how heavy the thing is. */
export interface SpringToken {
  stiffness: number;
  damping: number;
  mass: number;
}

export interface Point {
  x: number;
  y: number;
}

export interface Box {
  left: number;
  top: number;
  width: number;
  height: number;
}

export function clamp(value: number, min: number, max: number): number {
  return Math.min(max, Math.max(min, value));
}

/** Rounds to `digits` decimals and drops the noise of binary floats (0.30000000000000004). */
export function roundTo(value: number, digits: number): number {
  const factor = 10 ** digits;
  const rounded = Math.round(value * factor) / factor;
  return Object.is(rounded, -0) ? 0 : rounded;
}

/** Steps between two samples of a spring, and how close to rest counts as resting. */
const SAMPLE_STEP_SECONDS = 1 / 60;
const INTEGRATION_STEP_SECONDS = 1 / 2000;
const REST_DELTA = 0.001;
const REST_SPEED = 0.02;
const MAX_SPRING_SECONDS = 4;

/**
 * Position of a spring released at 0 towards 1, sampled 60 times a second
 * until it rests (or 4 s pass). The first sample is 0 and the last 1.
 */
export function simulateSpring(spring: SpringToken): { samples: number[]; seconds: number } {
  const samples = [0];
  let position = 0;
  let velocity = 0;
  let elapsed = 0;
  let nextSample = SAMPLE_STEP_SECONDS;
  while (elapsed < MAX_SPRING_SECONDS) {
    const force = -spring.stiffness * (position - 1) - spring.damping * velocity;
    velocity += (force / spring.mass) * INTEGRATION_STEP_SECONDS;
    position += velocity * INTEGRATION_STEP_SECONDS;
    elapsed += INTEGRATION_STEP_SECONDS;
    if (elapsed + 1e-9 >= nextSample) {
      samples.push(position);
      nextSample += SAMPLE_STEP_SECONDS;
      if (Math.abs(position - 1) < REST_DELTA && Math.abs(velocity) < REST_SPEED) {
        break;
      }
    }
  }
  samples[samples.length - 1] = 1;
  return { samples, seconds: (samples.length - 1) * SAMPLE_STEP_SECONDS };
}

/**
 * The spring as a CSS easing: `linear(0, 0.08, …, 1.04, …, 1)` (overshoot
 * included) and the duration a transition with it has to run, rounded to
 * 10 ms. globals.css keeps these strings; a unit test regenerates them.
 */
export function springToCssLinear(spring: SpringToken): { easing: string; durationMs: number } {
  const { samples, seconds } = simulateSpring(spring);
  const points = samples.map((sample) => String(roundTo(sample, 3)));
  return { easing: `linear(${points.join(", ")})`, durationMs: Math.round((seconds * 1000) / 10) * 10 };
}

/** Whether a spring overshoots its target (damping ratio below 1). */
export function dampingRatio(spring: SpringToken): number {
  return spring.damping / (2 * Math.sqrt(spring.stiffness * spring.mass));
}

/** `cubic-bezier(…)` of four control values. */
export function cubicBezierCss(points: readonly [number, number, number, number]): string {
  return `cubic-bezier(${points.join(", ")})`;
}

/**
 * How a card tilts towards the pointer: rotation around both axes (degrees,
 * at most `maxDegrees` at an edge) and where the glare sits (percent of the
 * card). A pointer outside the card counts as on its edge.
 */
export function tiltFromPointer(
  pointer: Point,
  box: Box,
  maxDegrees: number,
): { rotateX: number; rotateY: number; glareX: number; glareY: number } {
  const relativeX = box.width > 0 ? clamp((pointer.x - box.left) / box.width, 0, 1) : 0.5;
  const relativeY = box.height > 0 ? clamp((pointer.y - box.top) / box.height, 0, 1) : 0.5;
  return {
    // The top edge comes forward when the pointer is near it, the right edge when it is to the right.
    rotateX: roundTo((0.5 - relativeY) * 2 * maxDegrees, 3),
    rotateY: roundTo((relativeX - 0.5) * 2 * maxDegrees, 3),
    glareX: roundTo(relativeX * 100, 2),
    glareY: roundTo(relativeY * 100, 2),
  };
}

/** How far a button follows the pointer: a share of the distance from its centre, at most `max` px. */
export function magneticOffset(pointer: Point, box: Box, strength: number, max: number): Point {
  const centreX = box.left + box.width / 2;
  const centreY = box.top + box.height / 2;
  return {
    x: roundTo(clamp((pointer.x - centreX) * strength, -max, max), 2),
    y: roundTo(clamp((pointer.y - centreY) * strength, -max, max), 2),
  };
}

/** Fast at first, settling at the end; 0 → 0 and 1 → 1. */
export function easeOutCubic(progress: number): number {
  const t = clamp(progress, 0, 1);
  return 1 - (1 - t) ** 3;
}

/**
 * A number counting from `from` to `to`: the value after `elapsedMs` of
 * `durationMs`, rounded to the target's `fractionDigits` so the text never
 * shows more decimals than the final one.
 */
export function countUpValue(
  from: number,
  to: number,
  elapsedMs: number,
  durationMs: number,
  fractionDigits = 0,
): number {
  if (durationMs <= 0 || elapsedMs >= durationMs) {
    return to;
  }
  return roundTo(from + (to - from) * easeOutCubic(elapsedMs / durationMs), fractionDigits);
}

/** Decimals a value is shown with (3 → 0, 2.5 → 1, 0.125 → 3), at most 4. */
export function fractionDigitsOf(value: number): number {
  for (let digits = 0; digits < 4; digits += 1) {
    if (roundTo(value, digits) === value) {
      return digits;
    }
  }
  return 4;
}

/**
 * Moves `current` towards `target` by the share a damped follower covers in
 * `deltaSeconds` (`rate` per second), the same at 30 and at 144 frames a
 * second.
 */
export function approach(current: number, target: number, rate: number, deltaSeconds: number): number {
  return current + (target - current) * (1 - Math.exp(-rate * Math.max(0, deltaSeconds)));
}

/** The middle of a list of frame times (milliseconds); 0 for none. */
export function medianOf(values: readonly number[]): number {
  if (values.length === 0) {
    return 0;
  }
  const sorted = [...values].sort((left, right) => left - right);
  const middle = Math.floor(sorted.length / 2);
  return sorted.length % 2 === 1 ? (sorted[middle] ?? 0) : ((sorted[middle - 1] ?? 0) + (sorted[middle] ?? 0)) / 2;
}
