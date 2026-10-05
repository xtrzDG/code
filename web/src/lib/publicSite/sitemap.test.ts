import { describe, expect, it } from "vitest";

import { publicPageRests, sitemapEntries } from "./sitemap";

describe("sitemap", () => {
  it("lists the home and the niches, and the legal pages only once they are final", () => {
    expect(publicPageRests(["restaurant", "hotel"], false)).toEqual(["", "/for/restaurant", "/for/hotel"]);
    expect(publicPageRests([], true)).toEqual(["", "/terms", "/privacy", "/dpa", "/security", "/contact"]);
  });

  it("gives every page in every language with the others as alternates", () => {
    const entries = sitemapEntries("https://app.example.com/", ["", "/for/hotel"]);

    expect(entries.map((entry) => entry.url)).toEqual([
      "https://app.example.com/ka",
      "https://app.example.com/ru",
      "https://app.example.com/en",
      "https://app.example.com/ka/for/hotel",
      "https://app.example.com/ru/for/hotel",
      "https://app.example.com/en/for/hotel",
    ]);
    expect(entries[4]?.alternates.languages).toEqual({
      ka: "https://app.example.com/ka/for/hotel",
      ru: "https://app.example.com/ru/for/hotel",
      en: "https://app.example.com/en/for/hotel",
    });
    expect(entries[0]?.priority).toBe(1);
    expect(entries[3]?.priority).toBe(0.8);
  });
});
