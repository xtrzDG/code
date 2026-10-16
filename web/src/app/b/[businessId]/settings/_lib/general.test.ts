import { describe, expect, it } from "vitest";

import {
  buildGeneralChanges,
  generalFormFrom,
  hasChanges,
  languageChoices,
  parseRetentionDays,
  toggleLanguage,
} from "./general";
import { business } from "./settingsFixtures";

describe("general settings", () => {
  it("sends nothing when nothing changed", () => {
    const result = buildGeneralChanges(business, generalFormFrom(business));
    expect(result).toEqual({ ok: true, changes: {} });
    expect(result.ok && hasChanges(result.changes)).toBe(false);
  });

  it("sends only the changed fields, trimmed", () => {
    const form = { ...generalFormFrom(business), name: "  Café Rustaveli ", city: "", retentionDays: "30" };
    expect(buildGeneralChanges(business, form)).toEqual({
      ok: true,
      changes: { name: "Café Rustaveli", city: "", recording_retention_days: 30 },
    });
  });

  it("moves the default language when it is no longer spoken", () => {
    const form = { ...generalFormFrom(business), languages: ["en", "ru"] };
    expect(buildGeneralChanges(business, form)).toEqual({
      ok: true,
      changes: { languages: ["en", "ru"], default_language: "en" },
    });
  });

  it("refuses an empty name, no languages and a bad retention", () => {
    const form = { ...generalFormFrom(business), name: " ", languages: [], retentionDays: "0" };
    expect(buildGeneralChanges(business, form)).toEqual({
      ok: false,
      errors: { name: "required", languages: "languages", retentionDays: "retention" },
    });
    expect(buildGeneralChanges(business, { ...generalFormFrom(business), city: "x".repeat(121) })).toEqual({
      ok: false,
      errors: { city: "tooLong" },
    });
  });

  it("parses retention days in 1..3650", () => {
    expect(parseRetentionDays("90")).toBe(90);
    expect(parseRetentionDays(" 3650 ")).toBe(3650);
    expect(parseRetentionDays("3651")).toBeNull();
    expect(parseRetentionDays("1.5")).toBeNull();
    expect(parseRetentionDays("")).toBeNull();
  });

  it("merges and toggles languages in a stable order", () => {
    const choices = languageChoices(["ka", "en"], ["ka", "ru", "en"], ["tr"]);
    expect(choices).toEqual(["ka", "en", "ru", "tr"]);
    expect(toggleLanguage(["en"], "ka", true, choices)).toEqual(["ka", "en"]);
    expect(toggleLanguage(["ka", "en"], "ka", false, choices)).toEqual(["en"]);
    expect(toggleLanguage(["ka"], "fr", true, choices)).toEqual(["ka", "fr"]);
  });
});
