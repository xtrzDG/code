/**
 * What owners say about the assistant, for the landing page. Only real
 * quotes from real owners, with their written consent to publish their
 * name, business and words, go here; the section stays hidden while the
 * list for a language is empty. Each entry is in the language it was said
 * in and shown on that language's page.
 *
 * Example:
 *
 *     {
 *       locale: "ru",
 *       quote: "Ночные брони больше не теряются.",
 *       author: "Нино Беридзе",
 *       business: "Кафе «Руставели», Тбилиси",
 *       nicheKey: "restaurant",
 *     }
 */

import type { Locale } from "@/i18n/config";

export interface Testimonial {
  locale: Locale;
  quote: string;
  author: string;
  business: string;
  /** The kind of business, so a niche page shows its own owners first. */
  nicheKey?: string;
}

export const TESTIMONIALS: readonly Testimonial[] = [];
