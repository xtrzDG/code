import { describe, expect, it } from "vitest";

import { CONFETTI_CLAY_SAND, FALLBACK_INK, confettiPalette } from "./confettiPalette";

function hueAndSaturation(hex: string): { hue: number; saturation: number } {
  const [red, green, blue] = [1, 3, 5].map((offset) => parseInt(hex.slice(offset, offset + 2), 16) / 255) as [number, number, number];
  const max = Math.max(red, green, blue);
  const min = Math.min(red, green, blue);
  const lightness = (max + min) / 2;
  const delta = max - min;
  if (delta === 0) {
    return { hue: 0, saturation: 0 };
  }
  const saturation = lightness > 0.5 ? delta / (2 - max - min) : delta / (max + min);
  const hue = max === red ? ((green - blue) / delta) % 6 : max === green ? (blue - red) / delta + 2 : (red - green) / delta + 4;
  return { hue: (hue * 60 + 360) % 360, saturation };
}

describe("go-live confetti colours", () => {
  it("are clay and sand: warm hues between red-orange and amber", () => {
    for (const color of CONFETTI_CLAY_SAND) {
      const { hue } = hueAndSaturation(color);
      expect(hue, color).toBeGreaterThanOrEqual(15);
      expect(hue, color).toBeLessThanOrEqual(40);
    }
  });

  it("end with the page's ink, read from the canvas's computed colour", () => {
    expect(confettiPalette("rgb(29, 28, 26)")).toEqual([...CONFETTI_CLAY_SAND, "rgb(29, 28, 26)"]);
    expect(confettiPalette("#1d1c1a").at(-1)).toBe("#1d1c1a");
  });

  it("fall back to the dark theme's ink when the colour is missing or odd", () => {
    expect(confettiPalette(null).at(-1)).toBe(FALLBACK_INK);
    expect(confettiPalette("").at(-1)).toBe(FALLBACK_INK);
    expect(confettiPalette("var(--ink)").at(-1)).toBe(FALLBACK_INK);
  });
});
