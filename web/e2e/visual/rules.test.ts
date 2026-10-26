/**
 * The review gate's rules (gate.ts) as plain functions: the palette as the
 * browser computed it (palette.ts, the same maths as
 * tests/platform/test_palette_guard.py) and the phone height budgets
 * (heights.ts).
 */

import { describe, expect, it } from "vitest";

import { phoneScreensAllowed } from "./heights";
import { hueFamily, offPalette, type Rgba, type SeenColour } from "./palette";

function rgb(hex: string, alpha = 1): Rgba {
  const value = Number.parseInt(hex.replace("#", ""), 16);
  return [(value >> 16) & 0xff, (value >> 8) & 0xff, value & 0xff, alpha];
}

function seen(hex: string, property = "color", alpha = 1): SeenColour {
  return { rgba: rgb(hex, alpha), property, count: 2, sample: 'span.badge "Done"' };
}

describe("the palette rule", () => {
  it("names the family of every retired colour, as the source guard does", () => {
    const retired: Record<string, string> = {
      "#4f46e5": "indigo",
      "#6366f1": "indigo",
      "#34d399": "green",
      "#38bdf8": "cyan",
      "#4a6739": "green",
      "#a9bf94": "green",
      "#2f7d4f": "green",
      "#8e5a9b": "purple",
      "#0f766e": "cyan",
    };
    for (const [colour, family] of Object.entries(retired)) {
      expect(hueFamily(rgb(colour)), colour).toBe(family);
    }
  });

  it("lets the palette itself through: neutrals, clay, olive, ochre, brick and slate", () => {
    for (const colour of ["#ad5732", "#e19a75", "#5c5a2e", "#c2bd8c", "#86570f", "#b0362b", "#3d5c79", "#98b0c8", "#141311", "#f6f5f2"]) {
      expect(hueFamily(rgb(colour)), colour).toBeNull();
    }
  });

  it("reports a banned colour with where it was used, and nothing allowed or transparent", () => {
    const sage = rgb("#7a9a6a");
    const found = offPalette(
      [seen("#34d399", "background-color"), seen("#7a9a6a", "fill"), seen("#8cc29b", "stroke"), seen("#6366f1", "color", 0), seen("#ad5732")],
      [sage],
    );
    expect(found).toEqual(['green rgb(52 211 153) on background-color, 2×: span.badge "Done"']);
  });

  it("matches an allowed token within a unit of rounding", () => {
    expect(offPalette([seen("#5b9b3b")], [rgb("#5a9a3a")])).toEqual([]);
    expect(offPalette([seen("#5f9f3f")], [rgb("#5a9a3a")])).toHaveLength(1);
  });
});

describe("the phone height rule", () => {
  it("allows four screens unless a page has its own budget", () => {
    expect(phoneScreensAllowed("/b/business_1/customers")).toBe(4);
    expect(phoneScreensAllowed("/b/business_1/overview")).toBe(4.25);
    expect(phoneScreensAllowed("/b/business_1/inbox/conversation_1")).toBe(4);
    expect(phoneScreensAllowed("/b/business_1/assistant/knowledge")).toBe(7);
    expect(phoneScreensAllowed("/b/business_1/settings")).toBe(4.75);
    expect(phoneScreensAllowed("/b/business_1/settings/team")).toBe(4);
    expect(phoneScreensAllowed("/admin/clients/business_1")).toBe(8.25);
  });
});
