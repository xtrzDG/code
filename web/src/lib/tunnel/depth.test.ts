import { describe, expect, it } from "vitest";

import { advance, alive, burst, GRAVITY, RING_COUNT, RING_GAP, ringsAt, seededRandom } from "./depth";

describe("tunnel rings", () => {
  it("surround the screen and recede, fading with depth", () => {
    const rings = ringsAt(0);
    expect(rings).toHaveLength(RING_COUNT + 1);
    expect(rings[0]).toEqual({ key: -1, z: RING_GAP, opacity: 0 });
    expect(rings[1]).toEqual({ key: 0, z: -0, opacity: 1 });
    expect(rings.at(-1)?.z).toBe(-(RING_COUNT - 1) * RING_GAP);
    const opacities = rings.slice(1).map((ring) => ring.opacity);
    expect([...opacities].sort((a, b) => b - a)).toEqual(opacities);
  });

  it("keep their keys when the owner moves a step deeper", () => {
    const before = ringsAt(2, 3);
    const after = ringsAt(3, 3);
    const ring = (key: number, list: typeof before) => list.find((item) => item.key === key);
    // The ring that was one step ahead now surrounds the screen.
    expect(ring(3, before)?.z).toBe(-RING_GAP);
    expect(ring(3, after)?.z).toBe(-0);
    // The one around the screen is passed: behind the viewer, invisible.
    expect(ring(2, after)).toEqual({ key: 2, z: RING_GAP, opacity: 0 });
  });
});

describe("confetti", () => {
  it("is reproducible with a seed", () => {
    const first = burst(5, { x: 100, y: 200 }, ["#111", "#222"], seededRandom(7));
    const second = burst(5, { x: 100, y: 200 }, ["#111", "#222"], seededRandom(7));
    expect(first).toEqual(second);
    expect(first.map((particle) => particle.color)).toEqual(["#111", "#222", "#111", "#222", "#111"]);
    expect(first.every((particle) => particle.x === 100 && particle.y === 200)).toBe(true);
  });

  it("falls a default colour back on an empty palette", () => {
    expect(burst(1, { x: 0, y: 0 }, [], seededRandom(1))[0]?.color).toBe("#5b5bd6");
  });

  it("is pulled down and loses life as time passes", () => {
    const [particle] = burst(1, { x: 0, y: 0 }, ["#111"], seededRandom(3));
    if (!particle) {
      throw new Error("no particle");
    }
    const later = advance(particle, 0.5);
    expect(later.life).toBeCloseTo(particle.life - 0.5);
    expect(later.x).toBeCloseTo(particle.x + particle.vx * 0.5);
    expect(later.vy).toBeGreaterThan(particle.vy * Math.exp(-1.6 * 0.5));
    expect(later.vy).toBeLessThanOrEqual(particle.vy * Math.exp(-1.6 * 0.5) + GRAVITY * 0.5);
  });

  it("drops pieces that died or fell off the screen", () => {
    const base = burst(3, { x: 0, y: 0 }, ["#111"], seededRandom(5));
    const [first, second, third] = base;
    if (!first || !second || !third) {
      throw new Error("no particles");
    }
    const kept = alive([{ ...first, life: 0 }, { ...second, y: 2000 }, third], 800);
    expect(kept).toEqual([third]);
  });

  it("gives values between 0 and 1", () => {
    const random = seededRandom(42);
    for (let index = 0; index < 50; index += 1) {
      const value = random();
      expect(value).toBeGreaterThanOrEqual(0);
      expect(value).toBeLessThan(1);
    }
  });
});
