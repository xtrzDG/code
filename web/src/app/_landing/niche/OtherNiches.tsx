import Link from "next/link";

import type { NicheSummaryView } from "@/api/types";
import type { Locale } from "@/i18n/config";
import type { Translator } from "@/i18n/translate";
import { nichePath } from "@/lib/publicSite/paths";

import { Section } from "../Section";

/** Links to the pages of the other kinds of business. */
export function OtherNiches({
  t,
  locale,
  niches,
  current,
}: {
  t: Translator["t"];
  locale: Locale;
  niches: readonly NicheSummaryView[];
  current: string;
}) {
  const others = niches.filter((niche) => niche.key !== current);
  if (others.length === 0) {
    return null;
  }
  return (
    <Section id="other-niches" title={t("nichePage.otherTitle")}>
      <ul className="flex flex-wrap gap-2">
        {others.map((niche) => (
          <li key={niche.key}>
            <Link
              href={nichePath(locale, niche.key)}
              className="inline-flex rounded-full border border-line bg-surface px-3.5 py-1.5 text-sm text-ink transition-colors hover:bg-surface-muted focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-focus"
            >
              {niche.name}
            </Link>
          </li>
        ))}
      </ul>
    </Section>
  );
}
