/** Which owners' words a page shows: its language only, its kind of business first. */

import type { Testimonial } from "@/content/testimonials";

export function testimonialsFor(
  all: readonly Testimonial[],
  locale: string,
  nicheKey: string | null = null,
  limit = 3,
): Testimonial[] {
  const inLanguage = all.filter((entry) => entry.locale === locale);
  const own = nicheKey === null ? [] : inLanguage.filter((entry) => entry.nicheKey === nicheKey);
  const others = inLanguage.filter((entry) => !own.includes(entry));
  return [...own, ...others].slice(0, limit);
}
