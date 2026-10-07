import { describe, expect, it } from "vitest";

import { directionOf, matchLanguage, primaryLanguage } from "./language";
import { chooseLanguage } from "./negotiate";
import { HOSTED_CHAT_LANGUAGES, HOSTED_CHAT_TEXTS, hasHostedChatTexts, hostedChatTexts } from "./texts";

/** The languages of the website chat widget (app/gateways/http/static/widget/texts_*.js). */
const WIDGET_LANGUAGES = [
  "en", "de", "fr", "es", "it", "pt", "pl", "lt", "lv", "et", "fi", "nb", "ru", "uk", "kk",
  "ka", "hy", "az", "tr", "uz", "he", "ar", "fa", "ur", "hi", "zh", "ja", "ko", "vi",
];

describe("hosted chat language", () => {
  it("matches a browser tag to the business's languages, exactly or by primary language", () => {
    expect(matchLanguage("en-GB", ["ka", "en"])).toBe("en");
    expect(matchLanguage("pt", ["pt-BR"])).toBe("pt-BR");
    expect(matchLanguage("KA", ["ka"])).toBe("ka");
    expect(matchLanguage("zh_TW", ["zh-TW", "zh"])).toBe("zh-TW");
    expect(matchLanguage("de", ["ka", "en"])).toBeNull();
    expect(matchLanguage("  ", ["en"])).toBeNull();
    expect(primaryLanguage("pt-BR")).toBe("pt");
  });

  it("follows Accept-Language with q-values, else the default language", () => {
    const business = ["ka", "ru", "en", "he"];
    expect(chooseLanguage("de-DE,ru;q=0.8,en;q=0.9", business, "ka")).toBe("en");
    expect(chooseLanguage("he-IL,he;q=0.9", business, "ka")).toBe("he");
    expect(chooseLanguage("fr-FR", business, "ka")).toBe("ka");
    expect(chooseLanguage(null, business, "ka")).toBe("ka");
  });

  it("knows the right-to-left languages", () => {
    expect(directionOf("he")).toBe("rtl");
    expect(directionOf("ar-EG")).toBe("rtl");
    expect(directionOf("fa")).toBe("rtl");
    expect(directionOf("ka")).toBe("ltr");
  });
});

describe("hosted chat texts", () => {
  it("has every text in every language of the widget", () => {
    expect([...HOSTED_CHAT_LANGUAGES].sort()).toEqual([...WIDGET_LANGUAGES].sort());
    const keys = Object.keys(HOSTED_CHAT_TEXTS.en ?? {}).sort();
    for (const language of HOSTED_CHAT_LANGUAGES) {
      const texts: Record<string, string> = { ...HOSTED_CHAT_TEXTS[language] };
      expect(Object.keys(texts).sort(), language).toEqual(keys);
      for (const value of Object.values(texts)) {
        expect(value.trim(), language).not.toBe("");
      }
    }
  });

  it("falls back to English and uses the primary language of a regional tag", () => {
    expect(hostedChatTexts("ka-GE").loading).toBe("ჩატი იხსნება…");
    expect(hostedChatTexts("xx").loading).toBe("Opening the chat…");
    expect(hasHostedChatTexts("he-IL")).toBe(true);
    expect(hasHostedChatTexts("sw")).toBe(false);
  });
});
