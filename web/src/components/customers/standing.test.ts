import { describe, expect, it } from "vitest";

import { createTranslator } from "@/i18n/translate";
import { en } from "@/i18n/messages/en";
import { it as italian } from "@/i18n/messages/it";

import { standingLine } from "./standing";

describe("a customer's standing line", () => {
  it("names the standing and counts the visits in Italian", () => {
    const translator = createTranslator("it", italian);
    expect(standingLine(translator, "regular", 4)).toBe("Cliente abituale · 4 visite");
    expect(standingLine(translator, "regular", 1)).toBe("Cliente abituale · 1 visita");
    expect(standingLine(translator, "visited", 1)).toBe("Una visita · 1 visita");
  });

  it("is the standing alone before a first visit", () => {
    expect(standingLine(createTranslator("en", en), "new", 0)).toBe("New customer");
    expect(standingLine(createTranslator("it", italian), "returning", 0)).toBe("Cliente di ritorno");
  });

  it("speaks English too", () => {
    expect(standingLine(createTranslator("en", en), "regular", 1)).toBe("Regular customer · 1 visit");
  });
});
