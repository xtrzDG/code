import { readFileSync } from "node:fs";
import path from "node:path";
import { fileURLToPath } from "node:url";

import { describe, expect, it } from "vitest";

/**
 * Text on the business's accent on the hosted chat page (/c/{address})
 * takes the colour the page picks for that accent (--hc-on-accent, from
 * accentColors: white, else ink on a light accent, at WCAG AA and no more),
 * at full strength, like the widget's header beside it
 * (tests/channels/test_widget_text_contrast.py). A fixed white is
 * unreadable on a light accent; a faded colour falls below AA.
 */

const STYLES = fileURLToPath(new URL(".", import.meta.url));
const SHEETS = ["hostedChat.css", "hostedInfo.css"];

interface Rule {
  sheet: string;
  selector: string;
  declarations: Map<string, string>;
}

/** The innermost rules of a stylesheet (comments dropped), with their declarations. */
function rulesOf(sheet: string): Rule[] {
  const css = readFileSync(path.join(STYLES, sheet), "utf8").replace(/\/\*[\s\S]*?\*\//g, "");
  return [...css.matchAll(/([^{}]+)\{([^{}]*)\}/g)].map((match) => ({
    sheet,
    selector: (match[1] ?? "").trim(),
    declarations: new Map(
      (match[2] ?? "")
        .split(";")
        .map((declaration) => declaration.split(":"))
        .filter((parts) => parts.length >= 2)
        .map(([property = "", ...value]) => [property.trim(), value.join(":").trim()]),
    ),
  }));
}

const accentRules = SHEETS.flatMap(rulesOf).filter((rule) => rule.declarations.get("background") === "var(--hc-accent)");

describe("text on the accent of the hosted chat page", () => {
  it("is the colour picked for the accent, never a fixed one", () => {
    const coloured = accentRules.filter((rule) => rule.declarations.has("color"));

    expect(coloured.map((rule) => rule.selector)).toEqual(expect.arrayContaining([".hc-mark", ".hc-info-book"]));
    for (const rule of coloured) {
      expect(rule.declarations.get("color"), `${rule.sheet} ${rule.selector}`).toBe("var(--hc-on-accent)");
    }
  });

  it("is never faded", () => {
    for (const rule of accentRules) {
      expect(rule.declarations.has("opacity"), `${rule.sheet} ${rule.selector}`).toBe(false);
    }
  });
});
