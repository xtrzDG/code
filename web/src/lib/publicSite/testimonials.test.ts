import { describe, expect, it } from "vitest";

import type { Testimonial } from "@/content/testimonials";
import { TESTIMONIALS } from "@/content/testimonials";

import { testimonialsFor } from "./testimonials";

const entry = (locale: Testimonial["locale"], author: string, nicheKey?: string): Testimonial => ({
  locale,
  quote: "q",
  author,
  business: "b",
  ...(nicheKey ? { nicheKey } : {}),
});

describe("testimonials", () => {
  const all = [entry("it", "A", "hotel"), entry("en", "B"), entry("it", "C", "restaurant"), entry("it", "D", "restaurant")];

  it("shows only the page's language, the page's kind of business first", () => {
    expect(testimonialsFor(all, "it").map((item) => item.author)).toEqual(["A", "C", "D"]);
    expect(testimonialsFor(all, "it", "restaurant").map((item) => item.author)).toEqual(["C", "D", "A"]);
    expect(testimonialsFor(all, "it", "restaurant", 1).map((item) => item.author)).toEqual(["C"]);
    expect(testimonialsFor([entry("it", "A")], "en")).toEqual([]);
  });

  it("publishes no invented quotes", () => {
    expect(TESTIMONIALS).toEqual([]);
  });
});
