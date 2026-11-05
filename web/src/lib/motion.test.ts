import { readFileSync } from "node:fs";
import { fileURLToPath } from "node:url";

import { describe, expect, it } from "vitest";

import {
  DISTANCES,
  SPRINGS,
  cssMotionTokens,
  revealVariants,
  springTransition,
  staggerVariants,
  tweenTransition,
} from "./motion";
import { dampingRatio } from "./motionMath";

const MOTION_CSS = readFileSync(fileURLToPath(new URL("../styles/motion.css", import.meta.url)), "utf8");

describe("motion tokens", () => {
  it("are declared in the stylesheet with the values TypeScript computes", () => {
    const tokens = cssMotionTokens();
    expect(Object.keys(tokens)).toEqual(
      expect.arrayContaining(["--motion-fast", "--ease-standard", "--ease-spring-press", "--motion-spring-snappy"]),
    );
    for (const [name, value] of Object.entries(tokens)) {
      // A drift means: copy the new value from cssMotionTokens() into src/styles/motion.css.
      expect(MOTION_CSS, name).toContain(`${name}: ${value};`);
    }
  });

  it("keep the cabinet's springs firm and the playful ones lively", () => {
    expect(dampingRatio(SPRINGS.gentle)).toBeGreaterThan(0.95);
    expect(dampingRatio(SPRINGS.layout)).toBeGreaterThan(0.85);
    expect(dampingRatio(SPRINGS.snappy)).toBeGreaterThan(0.7);
    expect(dampingRatio(SPRINGS.bouncy)).toBeLessThan(0.6);
  });

  it("build motion transitions from the tokens", () => {
    expect(springTransition("snappy")).toEqual({ type: "spring", stiffness: 520, damping: 34, mass: 1, delay: 0 });
    expect(springTransition("gentle", 0.2)).toMatchObject({ delay: 0.2 });
    expect(tweenTransition("fast")).toEqual({ type: "tween", duration: 0.15, ease: [0.2, 0.8, 0.2, 1], delay: 0 });
    expect(tweenTransition("slow", "exit", 0.1)).toEqual({ type: "tween", duration: 0.42, ease: [0.4, 0, 1, 1], delay: 0.1 });
  });
});

describe("reveal variants", () => {
  it("rise from the tone's distance and land in place", () => {
    const cabinet = revealVariants("cabinet");
    expect(cabinet.hidden).toEqual({ opacity: 0, y: DISTANCES.cabinet, scale: 1, rotateX: 0 });
    expect(cabinet.visible).toMatchObject({ opacity: 1, y: 0, scale: 1, rotateX: 0, transition: { type: "tween" } });
  });

  it("come from further back with depth on the landing page", () => {
    const deep = revealVariants("landing", 1);
    expect(deep.hidden).toEqual({ opacity: 0, y: DISTANCES.landing, scale: 0.96, rotateX: 8 });
    expect(deep.visible).toMatchObject({ transition: { type: "spring", stiffness: SPRINGS.gentle.stiffness } });
    expect(revealVariants("landing", 0, 0.3).visible).toMatchObject({ transition: { delay: 0.3 } });
    expect(revealVariants("cabinet", 0, 0.1).visible).toMatchObject({ transition: { type: "tween", delay: 0.1 } });
  });

  it("stagger children by the tone's step", () => {
    expect(staggerVariants("landing", 0.1).visible).toEqual({ transition: { staggerChildren: 0.08, delayChildren: 0.1 } });
    expect(staggerVariants("cabinet").visible).toEqual({ transition: { staggerChildren: 0.035, delayChildren: 0 } });
    expect(staggerVariants("cabinet").hidden).toEqual({});
    expect(staggerVariants("landing", 0.2, 0.5).visible).toEqual({ transition: { staggerChildren: 0.5, delayChildren: 0.2 } });
  });
});
