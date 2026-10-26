/**
 * Label in Name (WCAG 2.5.3) in every language: where a control's name is a
 * text of its own (`aria-label`), it holds the words the control shows, in
 * their order (axe's `label-content-name-mismatch`, `src/test/labelInName.ts`).
 *
 * The dictionaries name such pairs alike: `remove` is what a button shows,
 * `removeLabel` its name ("Remove", "Remove {name}"). A field's own label is
 * a `…FieldLabel` (`addFieldLabel`), which pairs with nothing.
 */

import { describe, expect, it } from "vitest";

import { holdsShownWords } from "@/test/labelInName";

import { de } from "./messages/de";
import { en } from "./messages/en";
import { he } from "./messages/he";
import { ka } from "./messages/ka";
import { ru } from "./messages/ru";
import { interpolate, type MessageTree } from "./translate";

const LANGUAGES = { en, ru, ka, he, de } as const;

describe.each(Object.entries(LANGUAGES))("names that hold what they show, in %s", (_, messages) => {
  it("the setup ring says its title and percent as the bar shows them", () => {
    const { ring } = messages.setupGuide;
    const shown = `${ring.title} ${interpolate(ring.short, { percent: 40 })}`;

    expect(holdsShownWords(interpolate(ring.label, { percent: 40 }), shown)).toBe(true);
  });

  it("the map link of a shared place starts with its visible words", () => {
    const { place } = messages.conversationMedia;

    expect(holdsShownWords(interpolate(place.openMapLabel, { place: "Freedom Square" }), place.openMap)).toBe(true);
  });

  it("a calendar block's name starts with what the block shows", () => {
    const { block } = messages.bookingCalendar;
    const name = interpolate(block.label, { shown: "10:00–11:00, Anna Schmidt", place: "Nino", status: "Confirmed" });

    expect(holdsShownWords(name, "10:00–11:00 Anna Schmidt")).toBe(true);
  });
});

type Pair = { key: string; shown: string; name: string };

/** Every `xLabel` beside an `x` without placeholders, its placeholders filled. */
function shownAndNamed(tree: MessageTree, prefix = ""): Pair[] {
  return Object.entries(tree).flatMap(([key, value]): Pair[] => {
    if (value && typeof value === "object") {
      return shownAndNamed(value, `${prefix}${key}.`);
    }
    const shown = key.endsWith("Label") ? tree[key.slice(0, -"Label".length)] : undefined;
    if (typeof value !== "string" || typeof shown !== "string" || shown.includes("{")) {
      return [];
    }
    return [{ key: `${prefix}${key}`, shown, name: value.replace(/\{\w+\}/g, "Nino") }];
  });
}

describe.each(Object.entries(LANGUAGES))("every name beside what its control shows, in %s", (_, messages) => {
  it("holds the shown words", () => {
    const pairs = shownAndNamed(messages as unknown as MessageTree);
    const missing = pairs.filter((pair) => !holdsShownWords(pair.name, pair.shown)).map((pair) => `${pair.key}: "${pair.shown}" not in "${pair.name}"`);

    expect(pairs.length).toBeGreaterThan(25);
    expect(missing).toEqual([]);
  });
});

describe("the word matching", () => {
  it("ignores case, punctuation and what is in brackets, and keeps the order", () => {
    expect(holdsShownWords("Open in maps: Freedom Square (opens in a new tab)", "open in Maps")).toBe(true);
    expect(holdsShownWords("Setup: 40% done", "Setup 40 %")).toBe(true);
    expect(holdsShownWords("Open Freedom Square in maps", "Open in maps")).toBe(false);
    expect(holdsShownWords("Anna Schmidt, 10:00", "10:00 Anna Schmidt")).toBe(false);
  });
});
