import { describe, expect, it } from "vitest";

import {
  absoluteUrl,
  faqJsonLd,
  organizationJsonLd,
  schemaPrice,
  serializeJsonLd,
  serviceJsonLd,
  softwareJsonLd,
} from "./seo";

describe("structured data", () => {
  it("describes the organization with its contact when known", () => {
    expect(organizationJsonLd({ name: "W", url: "https://w.example", logo: "https://w.example/icon.svg" })).toEqual({
      "@context": "https://schema.org",
      "@type": "Organization",
      name: "W",
      url: "https://w.example",
      logo: "https://w.example/icon.svg",
    });
    expect(organizationJsonLd({ name: "W", url: "u", logo: "l", email: "hi@w.example" }).email).toBe("hi@w.example");
  });

  it("lists the plans as offers in the billed currency", () => {
    const data = softwareJsonLd({
      name: "W",
      description: "d",
      url: "https://w.example/en",
      language: "en",
      offers: [{ name: "Chat", price: schemaPrice(9900, 2), currency: "EUR" }],
    });
    expect(data.offers).toEqual([{ "@type": "Offer", name: "Chat", price: "99.00", priceCurrency: "EUR" }]);
    expect(schemaPrice(500, 0)).toBe("500");
  });

  it("turns questions and answers into a FAQ page", () => {
    expect(faqJsonLd([{ question: "Q?", answer: "A." }]).mainEntity).toEqual([
      { "@type": "Question", name: "Q?", acceptedAnswer: { "@type": "Answer", text: "A." } },
    ]);
  });

  it("describes a niche page as a service for that kind of business", () => {
    const data = serviceJsonLd({
      name: "AI assistant for restaurants",
      description: "d",
      url: "u",
      language: "ru",
      audience: "Restaurants",
      provider: "W",
    });
    expect(data.audience).toEqual({ "@type": "BusinessAudience", name: "Restaurants" });
    expect(data.provider).toEqual({ "@type": "Organization", name: "W" });
  });

  it("never lets a text close the script tag", () => {
    expect(serializeJsonLd({ name: "</script><b>" })).toBe('{"name":"\\u003c/script>\\u003cb>"}');
    expect(serializeJsonLd([{ a: 1 }])).toBe('[{"a":1}]');
  });

  it("joins the site's origin and a path", () => {
    expect(absoluteUrl("https://w.example/", "/ru")).toBe("https://w.example/ru");
    expect(absoluteUrl("https://w.example", "sitemap.xml")).toBe("https://w.example/sitemap.xml");
  });
});
