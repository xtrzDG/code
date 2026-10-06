import Link from "next/link";

import type { NicheSummaryView } from "@/api/types";
import { IconArrowRight } from "@/components/icons";
import { Stagger, StaggerItem } from "@/components/motion";
import type { Locale } from "@/i18n/config";
import type { Translator } from "@/i18n/translate";
import { nichePath } from "@/lib/publicSite/paths";

import { Section } from "./Section";

/**
 * The kinds of business the platform has scenarios for, from GET
 * /v1/catalog/niches; each opens its own page (/ru/for/restaurant).
 */
export function Niches({ t, niches, locale }: { t: Translator["t"]; niches: NicheSummaryView[] | null; locale: Locale }) {
  return (
    <Section
      id="niches"
      title={t("landing.niches.title")}
      subtitle={niches ? t("landing.niches.subtitle", { count: niches.length }) : undefined}
      glow="right"
    >
      {niches ? (
        <Stagger as="ul" step={0.04} className="grid gap-3 sm:grid-cols-2 lg:grid-cols-4">
          {niches.map((niche) => (
            <StaggerItem as="li" key={niche.key}>
              {/* The lift sits on its own element: the item's arrival leaves an inline transform behind. */}
              <Link
                href={nichePath(locale, niche.key)}
                className="motion-lift group flex h-full flex-col rounded-xl border border-line bg-surface p-4 focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-focus"
              >
                <span className="flex items-center justify-between gap-2 text-sm font-semibold text-ink">
                  {niche.name}
                  <IconArrowRight
                    className="size-4 shrink-0 text-ink-subtle transition-transform group-hover:translate-x-0.5 group-hover:text-accent rtl:-scale-x-100 rtl:group-hover:-translate-x-0.5"
                    aria-hidden
                  />
                </span>
                <span className="mt-1.5 line-clamp-3 text-sm text-ink-muted">{niche.description}</span>
              </Link>
            </StaggerItem>
          ))}
        </Stagger>
      ) : (
        <p className="text-sm text-ink-muted">{t("landing.niches.unavailable")}</p>
      )}
    </Section>
  );
}
