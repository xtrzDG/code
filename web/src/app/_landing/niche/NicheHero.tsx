import Link from "next/link";

import type { NicheSummaryView } from "@/api/types";
import { IconArrowRight, IconChevronRight } from "@/components/icons";
import { ButtonLink } from "@/components/ui";
import type { Translator } from "@/i18n/translate";
import { CREATE_PATH } from "@/lib/navigation";

import { HeroBackdrop } from "../HeroBackdrop";

/** The top of a niche's page: where it sits, what the assistant does for it and the calls to action. */
export function NicheHero({
  t,
  niche,
  home,
  hasDemo,
}: {
  t: Translator["t"];
  niche: NicheSummaryView;
  home: string;
  hasDemo: boolean;
}) {
  return (
    <section aria-labelledby="niche-title" className="relative isolate overflow-x-clip">
      <HeroBackdrop />
      <div className="relative mx-auto w-full max-w-6xl space-y-6 px-4 pt-10 pb-14 sm:px-6 sm:pt-16 sm:pb-20">
        <nav aria-label={t("nichePage.breadcrumb")} className="animate-rise">
          <ol className="flex flex-wrap items-center gap-1.5 text-sm text-ink-subtle">
            <li>
              <Link href={`${home}#niches`} className="transition-colors hover:text-ink">
                {t("nichePage.breadcrumb")}
              </Link>
            </li>
            <li aria-hidden>
              <IconChevronRight className="size-3.5" />
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
          <ButtonLink href={CREATE_PATH} size="lg" trailingIcon={<IconArrowRight className="size-4" aria-hidden />}>
            {t("nichePage.primary")}
          </ButtonLink>
          {hasDemo ? (
            <ButtonLink href="#demo" size="lg" variant="secondary">
              {t("nichePage.secondary")}
            </ButtonLink>
          ) : null}
        </div>
      </div>
    </section>
  );
}
