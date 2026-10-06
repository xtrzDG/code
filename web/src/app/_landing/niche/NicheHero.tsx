import Link from "next/link";
import type { ReactNode } from "react";

import type { NicheSummaryView } from "@/api/types";
import { IconArrowRight, IconChevronRight } from "@/components/icons";
import { ButtonLink } from "@/components/ui";
import type { Translator } from "@/i18n/translate";
import { CREATE_PATH } from "@/lib/navigation";

import { HeroBackdrop } from "../HeroBackdrop";

/**
 * The top of a niche's page: where it sits, what the assistant does for
 * it and the calls to action, beside a demo business of this kind to talk
 * to (`demo`) when one is configured.
 */
export function NicheHero({
  t,
  niche,
  home,
  demo = null,
}: {
  t: Translator["t"];
  niche: NicheSummaryView;
  home: string;
  demo?: ReactNode;
}) {
  return (
    <section aria-labelledby="niche-title" className="relative isolate overflow-x-clip">
      <HeroBackdrop />
      <div className="relative mx-auto grid w-full max-w-6xl items-center gap-10 px-4 pt-10 pb-14 sm:px-6 sm:pt-16 sm:pb-20 grid-cols-[minmax(0,1fr)] lg:grid-cols-[minmax(0,1.1fr)_minmax(0,1fr)] lg:gap-12">
        <div className="min-w-0 space-y-6">
          <nav aria-label={t("nichePage.breadcrumb")} className="animate-rise">
            <ol className="flex flex-wrap items-center gap-1.5 text-sm text-ink-subtle">
              <li>
                <Link href={`${home}#niches`} className="transition-colors hover:text-ink">
                  {t("nichePage.breadcrumb")}
                </Link>
              </li>
              <li aria-hidden>
                <IconChevronRight className="size-3.5 rtl:-scale-x-100" />
              </li>
              <li aria-current="page" className="text-ink-muted">
                {niche.name}
              </li>
            </ol>
          </nav>
          <p className="animate-rise text-sm font-medium text-accent [animation-delay:60ms]">{t("nichePage.eyebrow")}</p>
          <h1
            id="niche-title"
            className="landing-gradient-text max-w-3xl animate-rise text-4xl font-semibold tracking-tight text-balance [animation-delay:120ms] sm:text-5xl"
          >
            {t("nichePage.title", { niche: niche.name })}
          </h1>
          <div className="max-w-2xl animate-rise space-y-3 text-lg text-pretty text-ink-muted [animation-delay:180ms]">
            <p>{niche.description}</p>
            <p className="text-base">{t("nichePage.lead")}</p>
          </div>
          <div className="flex animate-rise flex-col gap-3 [animation-delay:240ms] sm:flex-row">
            <ButtonLink href={CREATE_PATH} size="lg" trailingIcon={<IconArrowRight className="size-4 rtl:-scale-x-100" aria-hidden />}>
              {t("nichePage.primary")}
            </ButtonLink>
            {demo ? (
              <ButtonLink href="#demo" size="lg" variant="secondary">
                {t("nichePage.secondary")}
              </ButtonLink>
            ) : null}
          </div>
        </div>
        {demo ? (
          <div className="relative mx-auto w-full min-w-0 max-w-md animate-rise [animation-delay:200ms] lg:max-w-none">{demo}</div>
        ) : null}
      </div>
    </section>
  );
}
