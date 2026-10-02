import { describe, expect, it } from "vitest";

import { describeError, parseApiError } from "@/api/errors";
import { en } from "@/i18n/messages/en";
import { ru } from "@/i18n/messages/ru";
import { createTranslator } from "@/i18n/translate";

import { BOOKING_REFUSAL_MESSAGES } from "./bookingRefusals";

describe("booking refusals in the user's language", () => {
  const tRu = createTranslator("ru", ru, en).t;
  const closedBody = {
    error: "validation_failed",
    message: "The business is closed at that time on 2026-12-31 (outside opening hours or a holiday).",
    reasons: [{ code: "closed", message: "The business is closed …", details: ["2026-12-31"] }],
  };

  it("names the reason instead of a generic title and the English sentence", () => {
    const description = describeError(parseApiError(422, closedBody), tRu, undefined, BOOKING_REFUSAL_MESSAGES);

    expect(description.title).toBe("2026-12-31 в это время заведение закрыто: вне часов работы или праздничный день.");
    expect(description.detail).toBeNull();
  });

  it("covers every refusal code the API sends", () => {
    for (const code of ["closed", "too_soon", "time_required", "taken", "party_too_large", "no_seating_resource"]) {
      const error = parseApiError(422, { error: "validation_failed", message: "x", reasons: [{ code, message: "x", details: ["4"] }] });
      const { title } = describeError(error, tRu, undefined, BOOKING_REFUSAL_MESSAGES);
      expect(title).not.toBe(tRu("errors.codes.validation_failed"));
      expect(title).not.toMatch(/[A-Za-z]{4}/);
    }
  });

  it("falls back to the generic text without a known reason", () => {
    const error = parseApiError(422, { error: "validation_failed", message: "Odd" });
    expect(describeError(error, tRu, undefined, BOOKING_REFUSAL_MESSAGES)).toEqual({
      title: tRu("errors.codes.validation_failed"),
      detail: "Odd",
      requestId: null,
    });
  });
});
