import { describe, expect, it } from "vitest";

import { createTranslator, interpolate } from "@/i18n/translate";
import { getMessages } from "@/i18n/messages";
import { en } from "@/i18n/messages/en";
import { splitUserValues, type SentenceWithUserValues } from "@/i18n/userValues";

import { handoffSummary } from "./handoffSummary";

const base = { summary: "Помощник был временно недоступен", summary_code: null, quoted_text: null, flagged_values: [] };

function inLocale(locale: "en" | "ru" | "ka") {
  return createTranslator(locale, getMessages(locale), en).t;
}

/** The summary as staff read it. */
function said(sentence: SentenceWithUserValues): string {
  return interpolate(sentence.text, sentence.values);
}

/** The words of the summary that are user content on the page. */
function userWords(sentence: SentenceWithUserValues): string[] {
  return splitUserValues(sentence.text, sentence.values).flatMap((part) => (part.kind === "value" ? [part.value] : []));
}

describe("handoff summary", () => {
  it("shows the model's own summary as it was written, as user content", () => {
    const view = handoffSummary({ ...base, summary: "Wants a window table" }, inLocale("ka"));
    expect(said(view.text)).toBe("Wants a window table");
    expect(userWords(view.text)).toEqual(["Wants a window table"]);
    expect(view.quote).toBeNull();
  });

  it("renders a platform code in the reader's language with the quoted message", () => {
    const view = handoffSummary(
      { ...base, summary_code: "model_unavailable", quoted_text: "Можно с собакой?" },
      inLocale("en"),
    );

    expect(said(view.text)).toBe("The assistant was briefly unavailable and could not answer.");
    expect(userWords(view.text)).toEqual([]);
    expect(view.quote).toEqual({ label: "The customer's message", text: "Можно с собакой?" });
  });

  it("lists the flagged values where the sentence has room for them", () => {
    const flagged = { ...base, summary_code: "unverified_values" as const, flagged_values: ["20 GEL", "19:30"] };

    expect(said(handoffSummary(flagged, inLocale("ru")).text)).toBe(
      "Помощник не отправил ответ: в нём были цифры или утверждения, которых нет в данных бизнеса (20 GEL, 19:30).",
    );
    expect(userWords(handoffSummary(flagged, inLocale("en")).text)).toEqual(["20 GEL, 19:30"]);
    expect(said(handoffSummary({ ...flagged, flagged_values: [] }, inLocale("ru")).text)).toBe(
      "Помощник не отправил ответ: в нём были цифры или утверждения, которых нет в данных бизнеса.",
    );
  });

  it("labels an undelivered reply as the reply, and erased data without a quote", () => {
    const undelivered = handoffSummary(
      { ...base, summary_code: "reply_undelivered", quoted_text: "Столик свободен" },
      inLocale("ka"),
    );
    expect(undelivered.quote?.label).toBe("პასუხი, რომელიც ვერ მივიდა");

    const erased = handoffSummary({ ...base, summary_code: "data_erased" }, inLocale("ru"));
    expect(said(erased.text)).toBe("Данные удалены по просьбе клиента.");
    expect(erased.quote).toBeNull();
  });
});
