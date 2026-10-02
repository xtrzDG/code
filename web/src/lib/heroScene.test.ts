import { describe, expect, it } from "vitest";

import { CHANNEL_MARKS } from "./channelMarks";
import {
  CAMERA_DISTANCE,
  CHANNEL_MARK_KEYS,
  ORBITS,
  cameraForScroll,
  depthOpacity,
  dustPositions,
  heroSceneMode,
  isFrameRateLow,
  messagePulseProgress,
  orbitPosition,
  pointerToParallax,
  seededRandom,
} from "./heroScene";

const CAPABLE = { prefersReducedMotion: false, hasWebGl: true, cores: 8, memoryGb: 8, saveData: false };

describe("which hero a device gets", () => {
  it("is the 3D scene on a capable device", () => {
    expect(heroSceneMode(CAPABLE)).toEqual({ mode: "3d" });
    // Browsers that hide cores or memory are given the benefit of the doubt.
    expect(heroSceneMode({ prefersReducedMotion: false, hasWebGl: true })).toEqual({ mode: "3d" });
  });

  it("is the still picture with reduced motion, without WebGL, with data saver or on a weak device", () => {
    expect(heroSceneMode({ ...CAPABLE, prefersReducedMotion: true })).toEqual({ mode: "static", reason: "reduced-motion" });
    expect(heroSceneMode({ ...CAPABLE, hasWebGl: false })).toEqual({ mode: "static", reason: "no-webgl" });
    expect(heroSceneMode({ ...CAPABLE, saveData: true })).toEqual({ mode: "static", reason: "save-data" });
    expect(heroSceneMode({ ...CAPABLE, cores: 2 })).toEqual({ mode: "static", reason: "low-power" });
    expect(heroSceneMode({ ...CAPABLE, memoryGb: 2 })).toEqual({ mode: "static", reason: "low-power" });
  });
});

describe("orbits", () => {
  it("give every channel one bubble, each with a mark", () => {
    expect(ORBITS.map((orbit) => orbit.channel).sort()).toEqual([...CHANNEL_MARK_KEYS].sort());
    for (const key of CHANNEL_MARK_KEYS) {
      expect(CHANNEL_MARKS[key].paths.length).toBeGreaterThan(0);
      expect(CHANNEL_MARKS[key].colors).toHaveLength(2);
    }
  });

  it("keep each bubble at its distance from the orb (apart from the bob)", () => {
    for (const orbit of ORBITS) {
      for (const seconds of [0, 1.5, 7, 40]) {
        const [x, y, z] = orbitPosition(orbit, seconds);
        expect(Math.hypot(x, y, z)).toBeCloseTo(orbit.radius, 0);
        expect(Math.abs(Math.hypot(x, y, z) - orbit.radius)).toBeLessThan(0.1);
      }
    }
  });

  it("start a flat, untilted orbit on its phase and move along it", () => {
    const flat = { channel: "phone" as const, radius: 2, tilt: 0, yaw: 0, speed: Math.PI / 2, phase: 0 };
    const [x0, , z0] = orbitPosition(flat, 0);
    expect([x0, z0]).toEqual([2, 0]);
    const [x1, , z1] = orbitPosition(flat, 1);
    expect(x1).toBeCloseTo(0, 4);
    expect(z1).toBeCloseTo(2, 4);
  });

  it("send one message at a time, each channel in turn", () => {
    expect(messagePulseProgress(0, 0, 6)).toBe(0);
    expect(messagePulseProgress(0, 0.475, 6)).toBeCloseTo(0.5);
    expect(messagePulseProgress(0, 1, 6)).toBeNull();
    expect(messagePulseProgress(1, 0.5, 6)).toBeNull();
    expect(messagePulseProgress(1, 1.1, 6)).toBeCloseTo(0);
    // The round repeats after every channel has sent one.
    expect(messagePulseProgress(0, 6.6 + 0.475, 6)).toBeCloseTo(0.5);
  });

  it("fade bubbles behind the orb", () => {
    expect(depthOpacity(3, 3)).toBe(1);
    expect(depthOpacity(-3, 3)).toBe(0.35);
    expect(depthOpacity(0, 3)).toBeCloseTo(0.675);
    expect(depthOpacity(10, 3)).toBe(1);
  });
});

describe("camera and pointer", () => {
  it("pull back, rise and fade as the hero scrolls away", () => {
    expect(cameraForScroll(0)).toEqual({ z: CAMERA_DISTANCE, y: 0, fade: 1 });
    expect(cameraForScroll(1)).toEqual({ z: CAMERA_DISTANCE + 4, y: 1.8, fade: 0.15 });
    expect(cameraForScroll(-1)).toEqual(cameraForScroll(0));
    expect(cameraForScroll(4)).toEqual(cameraForScroll(1));
  });

  it("maps the pointer to -1…1 with up positive", () => {
    expect(pointerToParallax(0, 0, 200, 100)).toEqual({ x: -1, y: 1 });
    expect(pointerToParallax(100, 50, 200, 100)).toEqual({ x: 0, y: 0 });
    expect(pointerToParallax(400, 300, 200, 100)).toEqual({ x: 1, y: -1 });
    expect(pointerToParallax(5, 5, 0, 0)).toEqual({ x: 0, y: 0 });
  });
});

describe("dust and frame rate", () => {
  it("repeats the same pseudo-random sequence for a seed", () => {
    const first = seededRandom(42);
    const second = seededRandom(42);
    const values = [first(), first(), first()];
    expect([second(), second(), second()]).toEqual(values);
    expect(values.every((value) => value >= 0 && value < 1)).toBe(true);
  });

  it("scatters dust in a shell around the orb", () => {
    const positions = dustPositions(50, 2, 4);
    expect(positions).toHaveLength(150);
    for (let index = 0; index < 50; index += 1) {
      const x = positions[index * 3] ?? 0;
      const y = (positions[index * 3 + 1] ?? 0) / 0.7;
      const z = positions[index * 3 + 2] ?? 0;
      const radius = Math.hypot(x, y, z);
      expect(radius).toBeGreaterThanOrEqual(1.999);
      expect(radius).toBeLessThanOrEqual(4.001);
    }
    expect(dustPositions(5, 2, 4)).toEqual(dustPositions(5, 2, 4));
  });

  it("calls the frame rate low only on enough slow frames", () => {
    expect(isFrameRateLow(Array.from({ length: 10 }, () => 50))).toBe(false);
    expect(isFrameRateLow(Array.from({ length: 60 }, () => 16))).toBe(false);
    expect(isFrameRateLow(Array.from({ length: 60 }, () => 33))).toBe(true);
  });
});
