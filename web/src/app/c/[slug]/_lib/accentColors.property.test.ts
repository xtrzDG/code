/**
 * Any business colour keeps WCAG AA on the hosted chat page and in the
 * widget it runs: text on the accent reads at 4.5:1 or better, and the page
 * paints the accent exactly as the widget's colors.js does.
 */

import { readFileSync } from "node:fs";
import { fileURLToPath } from "node:url";
import { runInNewContext } from "node:vm";

import fc from "fast-check";
import { describe, expect, it } from "vitest";

import { propertyParameters } from "@/test/properties";

import { accentColors, contrastRatio, type AccentColors } from "./accentColors";

const COLORS_JS = fileURLToPath(new URL("../../../../../../app/gateways/http/static/widget/colors.js", import.meta.url));

/** The widget's own `accentColors`, run as the browser runs it. */
function widgetAccentColors(): (hexColor: string) => AccentColors {
  const sandbox: { accentColors?: (hexColor: string) => AccentColors; THEMES: string[] } = { THEMES: ["light", "dark"] };
  runInNewContext(`${readFileSync(COLORS_JS, "utf8")}\nthis.accentColors = accentColors;`, sandbox);
  if (!sandbox.accentColors) {
    throw new Error("colors.js defines no accentColors");
  }
  return sandbox.accentColors;
}

const hexColors = fc
  .tuple(fc.integer({ min: 0, max: 255 }), fc.integer({ min: 0, max: 255 }), fc.integer({ min: 0, max: 255 }))
  .map((channels) => `#${channels.map((channel) => channel.toString(16).padStart(2, "0")).join("")}`);

describe("the business colour on the hosted chat page (property)", () => {
  it("always reads at WCAG AA", () => {
    fc.assert(
      fc.property(hexColors, (hexColor) => {
        const colors = accentColors(hexColor);
        return colors !== null && contrastRatio(colors.accent, colors.onAccent) >= 4.5;
      }),
      propertyParameters(),
    );
  });

  it("is painted exactly as the widget paints it", () => {
    const widget = widgetAccentColors();
    fc.assert(
      fc.property(hexColors, (hexColor) => {
        expect(accentColors(hexColor)).toEqual({ ...widget(hexColor) });
      }),
      propertyParameters(),
    );
  });

  it("keeps the owner's colour when one of the two texts reads on it", () => {
    expect(accentColors("#ad5732")).toEqual({ accent: "#ad5732", onAccent: "#ffffff" });
    expect(accentColors("#f59e0b")).toEqual({ accent: "#f59e0b", onAccent: "#1a1816" });
    expect(accentColors("#FFF")).toEqual({ accent: "#ffffff", onAccent: "#1a1816" });
  });

  it("darkens a mid-tone neither text reads on", () => {
    const colors = accentColors("#808080");
    expect(colors?.onAccent).toBe("#ffffff");
    expect(colors?.accent).not.toBe("#808080");
  });

  it("ignores anything that is not a hex colour", () => {
    expect(accentColors("red")).toBeNull();
    expect(accentColors("#12345")).toBeNull();
    expect(accentColors("")).toBeNull();
  });
});
