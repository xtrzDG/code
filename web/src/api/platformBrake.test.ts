import { describe, expect, it } from "vitest";

import { en } from "@/i18n/messages/en";
import { it as italian } from "@/i18n/messages/it";
import { createTranslator } from "@/i18n/translate";

import { describeError, parseApiError, type ReasonMessages } from "./errors";
import { platformBrakeText } from "./platformBrake";

/** The 409 the API answers while a platform brake holds (platform_brake_refusal). */
function braked(detail: string) {
  return parseApiError(409, {
    error: "conflict",
    message: "The platform holds every assistant's model work back for now.",
    reasons: [{ code: "platform_brake", message: "Held back.", details: [detail] }],
  });
}

const english = createTranslator("en", en);
const italianTexts = createTranslator("it", italian, en);

describe("a refusal by the platform brake", () => {
  it("names the brake from its detail", () => {
    expect(platformBrakeText("paused")).toBe("errors.platformBrake.paused");
    expect(platformBrakeText("budget_stop")).toBe("errors.platformBrake.budgetStop");
    expect(platformBrakeText(undefined)).toBe("errors.platformBrake.held");
  });

  it.each([
    ["paused", "paused"],
    ["budget_stop", "budgetStop"],
  ] as const)("reads %s in English and Italian, without the backend's English detail", (detail, key) => {
    for (const [texts, messages] of [
      [english, en],
      [italianTexts, italian],
    ] as const) {
      const described = describeError(braked(detail), texts.t);
      expect(described.title).toBe(messages.errors.platformBrake[key]);
      expect(described.detail).toBeNull();
    }
    expect(en.errors.platformBrake[key]).not.toBe(italian.errors.platformBrake[key]);
  });

  it("wins over a screen's own words for a conflict (menu import, autotest start)", () => {
    const described = describeError(braked("paused"), english.t, {
      conflict: "errors.codes.unknown_error",
      external_service_error: "errors.codes.unknown_error",
    });

    expect(described.title).toBe(en.errors.platformBrake.paused);
  });

  it("joins a screen's own refusal reasons (phone rental) and the default toast (alias suggestions)", () => {
    const own: ReasonMessages = { number_taken: () => ({ key: "errors.codes.not_found" }) };
    const taken = parseApiError(409, {
      error: "conflict",
      reasons: [{ code: "number_taken", message: "", details: [] }],
    });

    expect(describeError(braked("budget_stop"), italianTexts, undefined, own).title).toBe(
      italian.errors.platformBrake.budgetStop,
    );
    expect(describeError(taken, english, undefined, own).title).toBe(en.errors.codes.not_found);
    expect(describeError(braked("budget_stop"), english).title).toBe(en.errors.platformBrake.budgetStop);
  });

  it("leaves other conflicts to the generic text", () => {
    const other = parseApiError(409, { error: "conflict", message: "Version is being tested." });

    expect(describeError(other, english.t).title).toBe(en.errors.codes.conflict);
    expect(describeError(other, english.t).detail).toBe("Version is being tested.");
  });
});
