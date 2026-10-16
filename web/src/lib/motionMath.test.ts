import { describe, expect, it } from "vitest";

import {
  burstSparks,
  approach,
  clamp,
  countUpValue,
  cubicBezierCss,
  dampingRatio,
  easeOutCubic,
  fractionDigitsOf,
  magneticOffset,
  medianOf,
  roundTo,
  simulateSpring,
  springToCssLinear,
  tiltFromPointer,
} from "./motionMath";

const BOX = { left: 100, top: 50, width: 200, height: 100 };

describe("springs", () => {
  it("start at rest, overshoot when underdamped and end exactly on target", () => {
    const { samples, seconds } = simulateSpring({ stiffness: 300, damping: 18, mass: 1 });
    expect(samples[0]).toBe(0);
    expect(samples.at(-1)).toBe(1);
    expect(Math.max(...samples)).toBeGreaterThan(1.05);
    expect(seconds).toBeCloseTo((samples.length - 1) / 60, 6);
  });

  it("never overshoot when critically damped", () => {
    const { samples } = simulateSpring({ stiffness: 100, damping: 20, mass: 1 });
    expect(Math.max(...samples)).toBeLessThanOrEqual(1);
    expect(dampingRatio({ stiffness: 100, damping: 20, mass: 1 })).toBe(1);
  });

  it("stop after four seconds even when the spring would ring for longer", () => {
    const { seconds, samples } = simulateSpring({ stiffness: 100, damping: 0.5, mass: 1 });
    expect(seconds).toBeCloseTo(4, 1);
    expect(samples.at(-1)).toBe(1);
  });

  it("become a CSS linear() easing with the time a transition needs", () => {
    const { easing, durationMs } = springToCssLinear({ stiffness: 520, damping: 34, mass: 1 });
    expect(easing.startsWith("linear(0, ")).toBe(true);
    expect(easing.endsWith(", 1)")).toBe(true);
    expect(durationMs % 10).toBe(0);
    expect(durationMs).toBeGreaterThan(200);
    expect(durationMs).toBeLessThan(800);
  });

  it("write bezier curves for CSS", () => {
    expect(cubicBezierCss([0.2, 0.8, 0.2, 1])).toBe("cubic-bezier(0.2, 0.8, 0.2, 1)");
  });
});

describe("tilt", () => {
  it("is flat in the centre and strongest at the edges", () => {
    expect(tiltFromPointer({ x: 200, y: 100 }, BOX, 8)).toEqual({ rotateX: 0, rotateY: 0, glareX: 50, glareY: 50 });
    expect(tiltFromPointer({ x: 300, y: 50 }, BOX, 8)).toEqual({ rotateX: 8, rotateY: 8, glareX: 100, glareY: 0 });
    expect(tiltFromPointer({ x: 100, y: 150 }, BOX, 8)).toEqual({ rotateX: -8, rotateY: -8, glareX: 0, glareY: 100 });
  });

  it("treats a pointer outside the card as on its edge and an empty card as flat", () => {
    expect(tiltFromPointer({ x: 1000, y: -40 }, BOX, 5)).toMatchObject({ rotateX: 5, rotateY: 5 });
    expect(tiltFromPointer({ x: 3, y: 4 }, { left: 0, top: 0, width: 0, height: 0 }, 5)).toEqual({
      rotateX: 0,
      rotateY: 0,
      glareX: 50,
      glareY: 50,
    });
  });
});

describe("magnetic pull", () => {
  it("follows a share of the distance from the centre, up to a limit", () => {
    expect(magneticOffset({ x: 220, y: 100 }, BOX, 0.25, 8)).toEqual({ x: 5, y: 0 });
    expect(magneticOffset({ x: 400, y: 0 }, BOX, 0.25, 8)).toEqual({ x: 8, y: -8 });
    expect(magneticOffset({ x: 200, y: 100 }, BOX, 0.25, 8)).toEqual({ x: 0, y: 0 });
  });
});

describe("count up", () => {
  it("eases from the start value to the target", () => {
    expect(easeOutCubic(0)).toBe(0);
    expect(easeOutCubic(1)).toBe(1);
    expect(easeOutCubic(0.5)).toBeCloseTo(0.875);
    expect(easeOutCubic(2)).toBe(1);
    expect(countUpValue(0, 100, 0, 800)).toBe(0);
    expect(countUpValue(0, 100, 400, 800)).toBe(88);
    expect(countUpValue(0, 100, 800, 800)).toBe(100);
    expect(countUpValue(10, 2.5, 400, 800, 1)).toBe(3.4);
  });

  it("lands on the exact target when time is up or there is no time", () => {
    expect(countUpValue(0, 1234.5, 5000, 800)).toBe(1234.5);
    expect(countUpValue(0, 7, 0, 0)).toBe(7);
  });

  it("shows as many decimals as the target has", () => {
    expect(fractionDigitsOf(42)).toBe(0);
    expect(fractionDigitsOf(2.5)).toBe(1);
    expect(fractionDigitsOf(0.125)).toBe(3);
    expect(fractionDigitsOf(Math.PI)).toBe(4);
  });
});

describe("helpers", () => {
  it("clamp and round", () => {
    expect(clamp(5, 0, 1)).toBe(1);
    expect(clamp(-5, 0, 1)).toBe(0);
    expect(roundTo(0.1 + 0.2, 3)).toBe(0.3);
    expect(Object.is(roundTo(-0.0001, 2), 0)).toBe(true);
  });

  it("approach a target at the same pace whatever the frame rate", () => {
    const oneStep = approach(0, 1, 6, 1 / 30);
    const twoSteps = approach(approach(0, 1, 6, 1 / 60), 1, 6, 1 / 60);
    expect(oneStep).toBeCloseTo(twoSteps, 10);
    expect(approach(3, 1, 6, -1)).toBe(3);
  });

  it("find the median frame time", () => {
    expect(medianOf([])).toBe(0);
    expect(medianOf([30, 10, 20])).toBe(20);
    expect(medianOf([40, 10, 20, 30])).toBe(25);
  });
});

describe("burst", () => {
  it("spreads the sparks around a circle, every other one closer and later", () => {
    const sparks = burstSparks(4, 10);
    expect(sparks).toHaveLength(4);
    expect(sparks[0]).toEqual({ x: 0, y: -10, delay: 0 });
    expect(sparks[1]).toEqual({ x: 7, y: 0, delay: 0.05 });
    expect(sparks[2]?.y).toBe(10);
    expect(burstSparks(0, 10)).toEqual([]);
  });
});
