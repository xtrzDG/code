import { readFileSync } from "node:fs";
import path from "node:path";

import { render } from "@testing-library/react";
import type { ComponentType } from "react";
import { describe, expect, it } from "vitest";

import {
  AssistantOrbIllustration,
  DayZeroIllustration,
  InboxCalmIllustration,
  NoBookingsIllustration,
  NoInvoicesIllustration,
  OfflineIllustration,
} from "./index";

const ILLUSTRATIONS: Record<string, ComponentType<{ className?: string }>> = {
  "assistant-orb": AssistantOrbIllustration,
  "day-zero": DayZeroIllustration,
  "inbox-calm": InboxCalmIllustration,
  "no-bookings": NoBookingsIllustration,
  "no-invoices": NoInvoicesIllustration,
  offline: OfflineIllustration,
};

/**
 * The cabinet's palette for pictures: the graphite and paper neutrals, the
 * clay accent and its warm tones. Status colours (success, info…) carry a
 * meaning a drawing must not borrow.
 */
const PICTURE_TOKENS = new Set([
  "canvas",
  "surface",
  "surface-muted",
  "ink",
  "ink-muted",
  "ink-subtle",
  "line",
  "line-strong",
  "accent",
  "accent-solid",
  "accent-soft",
  "accent-ink",
  "on-accent",
  "tone-sand",
  "tone-rose",
]);

const THEME_COLORS = new Set(
  [...readFileSync(path.resolve(__dirname, "..", "..", "app", "globals.css"), "utf8").matchAll(/--color-([a-z0-9-]+):/g)].map(
    (match) => match[1],
  ),
);

function drawn(svg: SVGSVGElement) {
  const elements = [svg, ...svg.querySelectorAll("*")];
  const classes = elements.flatMap((element) => (element.getAttribute("class") ?? "").split(/\s+/));
  const tokens = classes
    .map((name) => /^(?:fill|stroke)-([a-z0-9-]+?)(?:\/\d+)?$/.exec(name)?.[1])
    .filter((token): token is string => token !== undefined && token !== "none");
  const paints = elements.flatMap((element) =>
    ["fill", "stroke", "stop-color", "style", "color"].map((name) => element.getAttribute(name) ?? "").filter(Boolean),
  );
  return { tokens, paints };
}

describe("the spot illustrations", () => {
  it.each(Object.entries(ILLUSTRATIONS))("%s is hidden from screen readers and named", (name, Illustration) => {
    const { container } = render(<Illustration className="w-40" />);
    const svg = container.querySelector("svg");
    expect(svg?.getAttribute("aria-hidden")).toBe("true");
    expect(svg?.getAttribute("focusable")).toBe("false");
    expect(svg?.dataset.illustration).toBe(name);
    expect(svg?.getAttribute("class")).toContain("w-40");
  });

  it.each(Object.entries(ILLUSTRATIONS))("%s paints with the theme's neutrals and clay only", (_name, Illustration) => {
    const { container } = render(<Illustration />);
    const { tokens, paints } = drawn(container.querySelector("svg") as SVGSVGElement);
    expect(tokens.length).toBeGreaterThan(3);
    for (const token of tokens) {
      expect(PICTURE_TOKENS.has(token), `fill/stroke-${token}`).toBe(true);
      expect(THEME_COLORS.has(token), `--color-${token} in globals.css`).toBe(true);
    }
    // No colour written out: only the theme's variables and gradients made of them.
    for (const paint of paints.map((value) => value.replace(/url\(#[\w-]+\)/g, "gradient"))) {
      expect(paint).not.toMatch(/#[0-9a-f]{3,8}\b|rgb|hsl|oklch|green|purple|indigo|cyan|mint|teal|violet/i);
      for (const variable of paint.matchAll(/var\(--([a-z0-9-]+)\)/g)) {
        expect(PICTURE_TOKENS.has(variable[1] ?? ""), `var(--${variable[1]})`).toBe(true);
      }
    }
  });

  it("gives every orb its own gradient, so two on a page do not share one", () => {
    const { container } = render(
      <>
        <AssistantOrbIllustration gradientId="first-orb" />
        <AssistantOrbIllustration gradientId="second-orb" />
      </>,
    );
    expect(container.querySelector("#first-orb")).not.toBeNull();
    expect(container.querySelector("#second-orb")).not.toBeNull();
    expect(container.querySelector('[fill="url(#second-orb)"]')).not.toBeNull();
  });
});
