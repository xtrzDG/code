import { ButtonLink } from "@/components/ui";
import { IconArrowRight } from "@/components/icons";
import type { Translator } from "@/i18n/translate";
import { LOGIN_PATH } from "@/lib/navigation";

import { HeroChat } from "./HeroChat";

/** What the product does, the two calls to action and a sample conversation. */
export function Hero({ t, trialDays }: { t: Translator["t"]; trialDays: number | null }) {
  return (
    <section aria-labelledby="hero-title" className="relative overflow-hidden">
      {/* A faint accent glow behind the headline; decorative only. */}
      <div
        className="pointer-events-none absolute inset-x-0 -top-40 h-[32rem] bg-[radial-gradient(50%_50%_at_50%_50%,color-mix(in_oklab,var(--accent-solid)_16%,transparent),transparent)]"
        aria-hidden
      />
      <div className="relative mx-auto grid w-full max-w-6xl items-center gap-12 px-4 pt-14 pb-16 sm:px-6 sm:pt-20 sm:pb-24 lg:grid-cols-[1.1fr_1fr] lg:gap-16">
        <div className="space-y-7">
          <p className="inline-flex items-center gap-2 rounded-full border border-line bg-surface px-3 py-1 text-xs font-medium text-ink-muted">
            <span className="size-1.5 rounded-full bg-accent-solid" aria-hidden />
            {t("landing.hero.eyebrow")}
          </p>
          <h1 id="hero-title" className="text-4xl font-semibold tracking-tight text-balance text-ink sm:text-5xl">
            {t("landing.hero.title")}
          </h1>
          <p className="max-w-xl text-lg text-pretty text-ink-muted">{t("landing.hero.subtitle")}</p>
          <div className="flex flex-col gap-3 sm:flex-row">
            <ButtonLink href={LOGIN_PATH} size="lg" trailingIcon={<IconArrowRight className="size-4" aria-hidden />}>
              {t("landing.hero.primary")}
            </ButtonLink>
            <ButtonLink href="#pricing" size="lg" variant="secondary">
              {t("landing.hero.secondary")}
            </ButtonLink>
          </div>
          <p className="text-sm text-ink-subtle">
            {trialDays ? `${t("landing.hero.trial", { days: trialDays })} · ` : null}
            {t("landing.hero.note")}
          </p>
        </div>
        <HeroChat t={t} />
      </div>
    </section>
  );
}
