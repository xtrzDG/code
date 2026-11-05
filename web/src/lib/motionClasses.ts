/**
 * The per-element motion settings of the public site's CSS motion
 * (src/styles/siteMotion.css) and of tilting cards, as classes rather than
 * a style attribute: the Content Security Policy refuses inline styles in
 * the server's HTML. Each setting takes one of the listed values, and
 * Tailwind generates exactly these classes (it reads this file).
 */

/** How far back a reveal comes from: 0 rises only, 1 also from smaller and tipped away. */
const REVEAL_DEPTH_CLASSES = {
  0: "",
  1: "[--reveal-depth:1]",
} as const;

/** Seconds a reveal waits after it is seen. */
const REVEAL_DELAY_CLASSES = {
  0: "",
  0.1: "[--reveal-delay:0.1s]",
  0.15: "[--reveal-delay:0.15s]",
  0.2: "[--reveal-delay:0.2s]",
  0.25: "[--reveal-delay:0.25s]",
  0.3: "[--reveal-delay:0.3s]",
} as const;

/** Seconds before the first item of a group arrives. */
const STAGGER_DELAY_CLASSES = {
  0: "",
  0.15: "[--stagger-delay:0.15s]",
  0.25: "[--stagger-delay:0.25s]",
} as const;

/** Seconds between two items of a group (0.08, the landing's STAGGER, is the stylesheet's default). */
const STAGGER_STEP_CLASSES = {
  0.04: "[--stagger-step:0.04s]",
  0.08: "",
  0.12: "[--stagger-step:0.12s]",
  0.14: "[--stagger-step:0.14s]",
  0.45: "[--stagger-step:0.45s]",
} as const;

/** A depth layer's drift: `speed` times 120 px over its block's way across the screen. */
const PARALLAX_CLASSES = {
  "-0.6": "[--parallax-shift:-72px]",
  "-0.3": "[--parallax-shift:-36px]",
  "0.3": "[--parallax-shift:36px]",
  "0.6": "[--parallax-shift:72px]",
} as const;

/** How many px a layer of a tilting card floats above it. */
const TILT_DEPTH_CLASSES = {
  8: "translate-z-[8px]",
  12: "translate-z-[12px]",
  14: "translate-z-[14px]",
  24: "translate-z-[24px]",
  28: "translate-z-[28px]",
  30: "translate-z-[30px]",
  34: "translate-z-[34px]",
} as const;

export type RevealDepth = keyof typeof REVEAL_DEPTH_CLASSES;
export type RevealDelay = keyof typeof REVEAL_DELAY_CLASSES;
export type StaggerDelay = keyof typeof STAGGER_DELAY_CLASSES;
export type StaggerStep = keyof typeof STAGGER_STEP_CLASSES;
export type ParallaxSpeed = -0.6 | -0.3 | 0.3 | 0.6;
export type TiltDepth = keyof typeof TILT_DEPTH_CLASSES;

export function revealClasses(depth: RevealDepth, delay: RevealDelay): string {
  return [REVEAL_DEPTH_CLASSES[depth], REVEAL_DELAY_CLASSES[delay]].filter(Boolean).join(" ");
}

export function staggerClasses(delay: StaggerDelay, step: StaggerStep): string {
  return [STAGGER_DELAY_CLASSES[delay], STAGGER_STEP_CLASSES[step]].filter(Boolean).join(" ");
}

export function parallaxClass(speed: ParallaxSpeed): string {
  return PARALLAX_CLASSES[String(speed) as keyof typeof PARALLAX_CLASSES];
}

export function tiltDepthClass(depth: TiltDepth): string {
  return TILT_DEPTH_CLASSES[depth];
}
