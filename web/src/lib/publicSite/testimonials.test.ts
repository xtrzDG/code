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
  const all = [entry("ru", "A", "hotel"), entry("en", "B"), entry("ru", "C", "restaurant"), entry("ru", "D", "restaurant")];

  it("shows only the page's language, the page's kind of business first", () => {
    expect(testimonialsFor(all, "ru").map((item) => item.author)).toEqual(["A", "C", "D"]);
    expect(testimonialsFor(all, "ru", "restaurant").map((item) => item.author)).toEqual(["C", "D", "A"]);
    expect(testimonialsFor(all, "ru", "restaurant", 1).map((item) => item.author)).toEqual(["C"]);
    expect(testimonialsFor(all, "ka")).toEqual([]);
  });

  it("publishes no invented quotes", () => {
    expect(TESTIMONIALS).toEqual([]);
  });
});
