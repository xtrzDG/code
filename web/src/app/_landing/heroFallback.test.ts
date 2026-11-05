import { readFileSync } from "node:fs";
import path from "node:path";

import { describe, expect, it } from "vitest";

import { CHANNEL_MARK_GRADIENTS, CHANNEL_MARK_KEYS, CHANNEL_MARKS } from "@/lib/channelMarks";
import { roundTo } from "@/lib/motionMath";

import { BUBBLE_ANGLES } from "./HeroFallback";

const POSTER_CSS = readFileSync(path.resolve(__dirname, "../../styles/heroPoster.css"), "utf8");

function ruleOf(index: number): string {
  const match = POSTER_CSS.match(new RegExp(`\\.hero-still-bubble\\[data-bubble="${index}"\\] \\{([^}]*)\\}`));
  return match?.[1] ?? "";
}

describe("the hero's poster", () => {
  it("places a bubble for every channel where the ellipse around the orb puts it", () => {
    expect(BUBBLE_ANGLES).toHaveLength(CHANNEL_MARK_KEYS.length);
    BUBBLE_ANGLES.forEach((degrees, index) => {
      const angle = (degrees * Math.PI) / 180;
      const rule = ruleOf(index);
      expect(rule).toContain(`left: ${roundTo(50 + 39 * Math.cos(angle), 2)}%;`);
      expect(rule).toContain(`top: ${roundTo(50 + 33 * Math.sin(angle), 2)}%;`);
      if (index > 0) {
        expect(rule).toContain(`animation-delay: ${roundTo(-index * 0.9, 1)}s;`);
      }
    });
  });

  it("paints each channel's badge with the mark's own two colours", () => {
    for (const channel of CHANNEL_MARK_KEYS) {
      const [from, to] = CHANNEL_MARKS[channel].colors;
      expect(CHANNEL_MARK_GRADIENTS[channel]).toBe(`bg-[linear-gradient(135deg,${from},${to})]`);
    }
  });
});
