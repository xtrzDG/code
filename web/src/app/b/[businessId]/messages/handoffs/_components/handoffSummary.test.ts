import { describe, expect, it } from "vitest";

import { createTranslator } from "@/i18n/translate";
import { getMessages } from "@/i18n/messages";
import { en } from "@/i18n/messages/en";

import { handoffSummary } from "./handoffSummary";

const base = { summary: "Помощник был временно недоступен", summary_code: null, quoted_text: null, flagged_values: [] };

function inLocale(locale: "en" | "ru" | "ka") {
  return createTranslator(locale, getMessages(locale), en).t;
}

describe("handoff summary", () => {
  it("shows the model's own summary as it was written", () => {
    expect(handoffSummary({ ...base, summary: "Wants a window table" }, inLocale("ka"))).toEqual({
      text: "Wants a window table",
      quote: null,
    });
  });

  it("renders a platform code in the reader's language with the quoted message", () => {
    const view = handoffSummary(
      { ...base, summary_code: "model_unavailable", quoted_text: "Можно с собакой?" },
      inLocale("en"),
    );

    expect(view.text).toBe("The assistant was briefly unavailable and could not answer.");
    expect(view.quote).toEqual({ label: "The customer's message", text: "Можно с собакой?" });
  });

  it("lists the flagged values where the sentence has room for them", () => {
    const flagged = { ...base, summary_code: "unverified_values" as const, flagged_values: ["20 GEL", "19:30"] };

    expect(handoffSummary(flagged, inLocale("ru")).text).toBe(
      "Помощник не отправил ответ: в нём были цифры, которых нет в данных бизнеса (20 GEL, 19:30).",
    );
    expect(handoffSummary({ ...flagged, flagged_values: [] }, inLocale("ru")).text).toBe(
      "Помощник не отправил ответ: в нём были цифры, которых нет в данных бизнеса.",
    );
  });

  it("labels an undelivered reply as the reply, and erased data without a quote", () => {
    const undelivered = handoffSummary(
      { ...base, summary_code: "reply_undelivered", quoted_text: "Столик свободен" },
      inLocale("ka"),
    );
    expect(undelivered.quote?.label).toBe("პასუხი, რომელიც ვერ მივიდა");

    expect(handoffSummary({ ...base, summary_code: "data_erased" }, inLocale("ru"))).toEqual({
      text: "Данные удалены по просьбе клиента.",
      quote: null,
    });
  });
});
