/**
 * Structured data (JSON-LD, schema.org) of the public pages: who offers
 * the product, what it costs, the questions and answers, and a niche's
 * page as a service. Search engines and assistants read it beside the
 * page; nothing in it says more than the page itself.
 */

export type JsonLd = Record<string, unknown>;

export interface OfferInput {
  name: string;
  /** Major units ("99", "293.50"), as schema.org expects. */
  price: string;
  currency: string;
}

/** An amount in minor units as schema.org's price text: 9900 EUR -> "99.00". */
export function schemaPrice(amountMinor: number, fractionDigits: number): string {
  return (amountMinor / 10 ** fractionDigits).toFixed(fractionDigits);
}

export function organizationJsonLd(input: { name: string; url: string; logo: string; email?: string | null }): JsonLd {
  return {
    "@context": "https://schema.org",
    "@type": "Organization",
    name: input.name,
    url: input.url,
    logo: input.logo,
    ...(input.email ? { email: input.email } : {}),
  };
}

export function softwareJsonLd(input: {
  name: string;
  description: string;
  url: string;
  language: string;
  offers: readonly OfferInput[];
}): JsonLd {
  return {
    "@context": "https://schema.org",
    "@type": "SoftwareApplication",
    name: input.name,
    description: input.description,
    url: input.url,
    inLanguage: input.language,
    applicationCategory: "BusinessApplication",
    operatingSystem: "Web",
    offers: input.offers.map((offer) => ({
      "@type": "Offer",
      name: offer.name,
      price: offer.price,
      priceCurrency: offer.currency,
    })),
  };
}

export function faqJsonLd(items: readonly { question: string; answer: string }[]): JsonLd {
  return {
    "@context": "https://schema.org",
    "@type": "FAQPage",
    mainEntity: items.map((item) => ({
      "@type": "Question",
      name: item.question,
      acceptedAnswer: { "@type": "Answer", text: item.answer },
    })),
  };
}

export function serviceJsonLd(input: {
  name: string;
  description: string;
  url: string;
  language: string;
  audience: string;
  provider: string;
}): JsonLd {
  return {
    "@context": "https://schema.org",
    "@type": "Service",
    name: input.name,
    description: input.description,
    url: input.url,
    inLanguage: input.language,
    serviceType: input.name,
    audience: { "@type": "BusinessAudience", name: input.audience },
    provider: { "@type": "Organization", name: input.provider },
  };
}

/** JSON for a <script type="application/ld+json">, with "<" escaped so no text closes the tag. */
export function serializeJsonLd(data: JsonLd | readonly JsonLd[]): string {
  return JSON.stringify(data).replace(/</g, "\\u003c");
}

/** An absolute address of a path on the site ("https://example.com" + "/ru"). */
export function absoluteUrl(origin: string, path: string): string {
  return `${origin.replace(/\/+$/, "")}${path.startsWith("/") ? path : `/${path}`}`;
}
