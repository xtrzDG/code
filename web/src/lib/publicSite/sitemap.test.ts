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
      "https://app.example.com/en",
      "https://app.example.com/it",
      "https://app.example.com/en/for/hotel",
      "https://app.example.com/it/for/hotel",
    ]);
    expect(entries[3]?.alternates.languages).toEqual({
      en: "https://app.example.com/en/for/hotel",
      it: "https://app.example.com/it/for/hotel",
    });
    expect(entries[0]?.priority).toBe(1);
    expect(entries[2]?.priority).toBe(0.8);
  });
});
