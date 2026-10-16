import { describe, expect, it } from "vitest";

import type { CountryProfileView, LanguageOption } from "@/api/types";

import { languageOptions } from "./languageOptions";

function option(tag: string, nativeName: string, displayName: string): LanguageOption {
  return { tag, native_name: nativeName, display_name: displayName, direction: "ltr" };
}

function profile(defaults: LanguageOption[], onRequest: LanguageOption[]): CountryProfileView {
  return {
    default_customer_languages: defaults,
    on_request_customer_languages: onRequest,
  } as unknown as CountryProfileView;
}

describe("customer language options", () => {
  it("are empty until the country profile has loaded", () => {
    expect(languageOptions(undefined)).toEqual([]);
  });

  it("list defaults first, then on-request languages, each once", () => {
    const options = languageOptions(
      profile(
        [option("ka", "ქართული", "georgian"), option("ru", "русский", "russian")],
        [option("ru", "русский", "russian"), option("tr", "türkçe", "turkish")],
      ),
    );

    expect(options.map((item) => item.tag)).toEqual(["ka", "ru", "tr"]);
  });

  it("start names with a capital, except Georgian script which has none", () => {
    const [georgian, russian] = languageOptions(
      profile([option("ka", "ქართული", "georgian"), option("ru", "русский", "russian")], []),
    );

    expect(georgian).toMatchObject({ native_name: "ქართული", display_name: "Georgian" });
    expect(russian).toMatchObject({ native_name: "Русский", display_name: "Russian" });
  });
});
