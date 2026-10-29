import { describe, expect, it } from "vitest";

import { describeError, parseApiError } from "@/api/errors";
import { en } from "@/i18n/messages/en";
import { it as italian } from "@/i18n/messages/it";
import { createTranslator } from "@/i18n/translate";

import { BOOKING_REFUSAL_MESSAGES } from "./bookingRefusals";

describe("booking refusals in the user's language", () => {
  const english = createTranslator("en", en);
  const translator = createTranslator("it", italian, en);
  const tIt = translator.t;
  const closedBody = {
    error: "validation_failed",
    message: "The business is closed at that time on 2026-12-31 (outside opening hours or a holiday).",
    reasons: [{ code: "closed", message: "The business is closed …", details: ["2026-12-31"] }],
  };

  it("names the reason instead of a generic title and the English sentence", () => {
    const description = describeError(parseApiError(422, closedBody), translator, undefined, BOOKING_REFUSAL_MESSAGES);

    expect(description.title).toBe("Il 2026-12-31 a quell'ora l'attività è chiusa: fuori dagli orari di apertura o per festività.");
    expect(description.detail).toBeNull();
  });

  it("covers every refusal code the API sends", () => {
    for (const code of [
      "closed",
      "too_soon",
      "time_required",
      "taken",
      "party_too_large",
      "no_seating_resource",
      "not_performed",
      "unknown_service",
    ]) {
      const error = parseApiError(422, { error: "validation_failed", message: "x", reasons: [{ code, message: "x", details: ["4"] }] });
      const { title } = describeError(error, translator, undefined, BOOKING_REFUSAL_MESSAGES);
      expect(title).not.toBe(tIt("errors.codes.validation_failed"));
      // Its own text, not the English one through the fallback.
      expect(title).not.toBe(describeError(error, english, undefined, BOOKING_REFUSAL_MESSAGES).title);
    }
  });

  it("falls back to the generic text without a known reason", () => {
    const error = parseApiError(422, { error: "validation_failed", message: "Odd" });
    expect(describeError(error, translator, undefined, BOOKING_REFUSAL_MESSAGES)).toEqual({
      title: tIt("errors.codes.validation_failed"),
      detail: "Odd",
      requestId: null,
    });
  });
});
