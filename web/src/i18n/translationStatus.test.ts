import { describe, expect, it } from "vitest";

import { CABINET_LANGUAGES, LOCALES } from "./config";
import { DICTIONARIES } from "./messages";
import { en } from "./messages/en";
import { missingTexts, textPaths, translationStatus, type TextTree } from "./translationStatus";

const reference: TextTree = {
  common: { save: "Save", cancel: "Cancel" },
  count: { one: "{count} item", other: "{count} items" },
};

describe("translation status", () => {
  it("counts a plural text once, whatever its categories", () => {
    expect([...textPaths(reference).keys()]).toEqual(["common.save", "common.cancel", "count"]);
    expect([...textPaths({ count: { one: "a", two: "b", other: "c" } }).keys()]).toEqual(["count"]);
  });

  it("lists what is missing and what is left over, with the share done", () => {
    const status = translationStatus(reference, { common: { save: "Speichern", old: "Alt" } });
    expect(status).toEqual({ total: 3, missing: ["common.cancel", "count"], extra: ["common.old"], percent: 33 });
    expect(missingTexts(reference, { common: { save: "Speichern" } })).toEqual({
      "common.cancel": "Cancel",
      count: { one: "{count} item", other: "{count} items" },
    });
  });

  it("finds every cabinet language complete and every other locale at least started", () => {
    for (const locale of LOCALES) {
      const status = translationStatus(en, DICTIONARIES[locale]);
      expect(status.extra, locale).toEqual([]);
      if (CABINET_LANGUAGES.includes(locale)) {
        expect(status.percent, locale).toBe(100);
      }
    }
  });
});
