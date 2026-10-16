import { describe, expect, it } from "vitest";

import { createTranslator } from "@/i18n/translate";
import { en } from "@/i18n/messages/en";
import { ka } from "@/i18n/messages/ka";
import { ru } from "@/i18n/messages/ru";

import { standingLine } from "./standing";

describe("a customer's standing line", () => {
  it("names the standing and counts the visits in Russian", () => {
    const translator = createTranslator("ru", ru);
    expect(standingLine(translator, "regular", 4)).toBe("Постоянный клиент · 4 визита");
    expect(standingLine(translator, "regular", 5)).toBe("Постоянный клиент · 5 визитов");
    expect(standingLine(translator, "visited", 1)).toBe("Был один раз · 1 визит");
  });

  it("is the standing alone before a first visit", () => {
    expect(standingLine(createTranslator("en", en), "new", 0)).toBe("New customer");
    expect(standingLine(createTranslator("ka", ka), "returning", 0)).toBe("დაბრუნებული კლიენტი");
  });

  it("speaks English too", () => {
    expect(standingLine(createTranslator("en", en), "regular", 1)).toBe("Regular customer · 1 visit");
  });
});
