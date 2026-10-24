import type { Testimonial } from "@/content/testimonials";
import type { Translator } from "@/i18n/translate";

import { Section } from "./Section";

/** Owners' own words (src/content/testimonials.ts); nothing at all while there are none. */
export function Testimonials({ t, items }: { t: Translator["t"]; items: readonly Testimonial[] }) {
  if (items.length === 0) {
    return null;
  }
  return (
    <Section id="testimonials" title={t("publicPricing.testimonials.title")}>
      <ul className="grid gap-4 md:grid-cols-3">
        {items.map((item) => (
          <li key={`${item.author}-${item.business}`} className="rounded-2xl border border-line bg-surface p-6">
            <blockquote className="text-pretty text-ink">“{item.quote}”</blockquote>
            <p className="mt-4 text-sm font-medium text-ink">{item.author}</p>
            <p className="text-sm text-ink-muted">{item.business}</p>
          </li>
        ))}
      </ul>
    </Section>
  );
}
