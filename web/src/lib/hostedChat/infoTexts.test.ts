import { describe, expect, it } from "vitest";

import { HOSTED_INFO_TEXTS, fillText, hostedInfoTexts } from "./infoTexts";
import { HOSTED_CHAT_LANGUAGES } from "./texts";

const ENGLISH = HOSTED_INFO_TEXTS.en!;
const placeholders = (text: string) => [...text.matchAll(/\{(\w+)\}/g)].map((match) => match[1]).sort();

describe("hosted page information texts", () => {
  it("speak every language of the hosted chat page", () => {
    expect(Object.keys(HOSTED_INFO_TEXTS).sort()).toEqual([...HOSTED_CHAT_LANGUAGES].sort());
  });

  it.each(Object.entries(HOSTED_INFO_TEXTS))("%s has every text, with the same placeholders", (_, texts) => {
    expect(Object.keys(texts).sort()).toEqual(Object.keys(ENGLISH).sort());
    for (const [key, text] of Object.entries(texts)) {
      expect(text.trim(), key).not.toBe("");
      expect(placeholders(text), key).toEqual(placeholders(ENGLISH[key as keyof typeof ENGLISH]));
    }
  });

  it("falls back to English and reads regional tags", () => {
    expect(hostedInfoTexts("pt-BR")).toBe(HOSTED_INFO_TEXTS.pt);
    expect(hostedInfoTexts("xx")).toBe(ENGLISH);
  });

  it("fills placeholders and keeps unknown ones", () => {
    expect(fillText("opens {day} at {time}", { day: "Monday", time: "10:00" })).toBe("opens Monday at 10:00");
    expect(fillText("until {time}", {})).toBe("until {time}");
  });
});
