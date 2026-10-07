import { describe, expect, it } from "vitest";

import { ApiError } from "@/api/errors";

import { isBotToken } from "./connectForm";
import {
  alternativeBotUsername,
  botHandle,
  botInitial,
  cleanBotToken,
  suggestBotUsername,
  tokenCheckProblem,
  transliterate,
} from "./telegramSetup";

const reason = (code: string) => ({ code, message: code, details: [] });

describe("the username suggested for @BotFather", () => {
  it("comes from the business name, in Latin letters, ending in _bot", () => {
    expect(suggestBotUsername("Mtsvane Ezo")).toBe("mtsvane_ezo_bot");
    expect(suggestBotUsername("მწვანე ეზო")).toBe("mtsvane_ezo_bot");
    expect(suggestBotUsername("Кафе «Пушкин»")).toBe("kafe_pushkin_bot");
    expect(suggestBotUsername("Café Crème")).toBe("cafe_creme_bot");
  });

  it("starts with a letter, stays within Telegram's 32 characters and never ends in bot twice", () => {
    expect(suggestBotUsername("24/7 Pizza")).toBe("pizza_bot");
    expect(suggestBotUsername("Salon Bot")).toBe("salon_bot");
    const long = suggestBotUsername("The Very Long Name Of A Family Restaurant In Old Tbilisi");
    expect(long.length).toBeLessThanOrEqual(32);
    expect(long).toMatch(/^[a-z][a-z0-9_]*[a-z0-9]_bot$/);
  });

  it("falls back to a neutral name when nothing Latin is left", () => {
    expect(suggestBotUsername("☕")).toBe("my_assistant_bot");
    expect(suggestBotUsername("")).toBe("my_assistant_bot");
  });

  it("offers another one when the first is taken", () => {
    expect(alternativeBotUsername("Mtsvane Ezo")).toBe("mtsvane_ezo2_bot");
  });

  it("transliterates Georgian and Cyrillic letters", () => {
    expect(transliterate("ჭაჭა")).toBe("chacha");
    expect(transliterate("Щука")).toBe("shchuka");
  });
});

describe("a pasted key", () => {
  it("loses the spaces and line breaks a copy brings along", () => {
    // A low-entropy stand-in with a real token's shape.
    const fake = `123456789:${"a".repeat(35)}`;
    const token = cleanBotToken(` ${fake.slice(0, 20)} ${fake.slice(20)} \n`);
    expect(token).toBe(fake);
    expect(isBotToken(token)).toBe(true);
    expect(isBotToken("not a token")).toBe(false);
  });

  it("is refused for its shape, unknown to Telegram, or could not be checked", () => {
    expect(tokenCheckProblem(new ApiError({ status: 422, code: "validation_failed", reasons: [reason("telegram_token_format")] }))).toBe(
      "format",
    );
    expect(
      tokenCheckProblem(new ApiError({ status: 422, code: "validation_failed", reasons: [reason("telegram_token_rejected")] })),
    ).toBe("rejected");
    expect(tokenCheckProblem(new ApiError({ status: 429, code: "rate_limited" }))).toBe("unavailable");
    expect(tokenCheckProblem(new ApiError({ status: 502, code: "external_service_error" }))).toBe("unavailable");
  });
});

describe("the bot it opens", () => {
  it("is shown by its handle and, without a photo, by its first letter", () => {
    expect(botHandle({ username: "mtsvane_ezo_bot" })).toBe("@mtsvane_ezo_bot");
    expect(botHandle({ username: "@cafe_bot" })).toBe("@cafe_bot");
    expect(botInitial({ username: "cafe_bot", display_name: "მწვანე ეზო" })).toBe("მ");
    expect(botInitial({ username: "cafe_bot", display_name: null })).toBe("C");
  });
});
