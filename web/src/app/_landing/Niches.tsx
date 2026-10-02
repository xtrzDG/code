import type { NicheSummaryView } from "@/api/types";
import type { Translator } from "@/i18n/translate";

import { Section } from "./Section";

/** The kinds of business the platform has scenarios for, from GET /v1/catalog/niches. */
export function Niches({ t, niches }: { t: Translator["t"]; niches: NicheSummaryView[] | null }) {
  return (
    <Section
      id="niches"
      title={t("landing.niches.title")}
      subtitle={niches ? t("landing.niches.subtitle", { count: niches.length }) : undefined}
    >
      {niches ? (
        <ul className="grid gap-3 sm:grid-cols-2 lg:grid-cols-4">
          {niches.map((niche) => (
            <li key={niche.key} className="rounded-xl border border-line bg-surface p-4">
              <h3 className="text-sm font-semibold text-ink">{niche.name}</h3>
              <p className="mt-1.5 line-clamp-3 text-sm text-ink-muted">{niche.description}</p>
            </li>
          ))}
        </ul>
      ) : (
        <p className="text-sm text-ink-muted">{t("landing.niches.unavailable")}</p>
      )}
    </Section>
  );
}
