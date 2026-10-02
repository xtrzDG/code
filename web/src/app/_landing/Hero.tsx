import { IconArrowRight } from "@/components/icons";
import { MagneticButton } from "@/components/motion";
import { ButtonLink } from "@/components/ui";
import type { Translator } from "@/i18n/translate";
import { LOGIN_PATH } from "@/lib/navigation";

import { HeroBackdrop } from "./HeroBackdrop";
import { HeroVisual } from "./HeroVisual";

/**
 * What the product does and the two calls to action, beside the assistant
 * in 3D (or its still picture). The text rises in with CSS, so it moves
 * from the first paint, before any script.
 */
export function Hero({ t, trialDays }: { t: Translator["t"]; trialDays: number | null }) {
  return (
    <section aria-labelledby="hero-title" className="relative isolate overflow-x-clip">
      <HeroBackdrop />
      <div className="relative mx-auto grid w-full max-w-6xl items-center gap-6 px-4 pt-12 pb-12 sm:px-6 sm:pt-20 sm:pb-20 lg:grid-cols-[1.2fr_1fr] lg:gap-8">
        <div className="space-y-7">
          <p className="inline-flex animate-rise items-center gap-2 rounded-full border border-line bg-surface/70 px-3 py-1 text-xs font-medium text-ink-muted backdrop-blur">
            <span className="relative flex size-1.5" aria-hidden>
              <span className="absolute inset-0 animate-ping rounded-full bg-accent-solid opacity-60" />
              <span className="relative size-1.5 rounded-full bg-accent-solid" />
            </span>
            {t("landing.hero.eyebrow")}
          </p>
          <h1
            id="hero-title"
            className="landing-gradient-text animate-rise text-4xl font-semibold tracking-tight text-balance [animation-delay:80ms] sm:text-5xl lg:max-w-[34rem] lg:text-[3.25rem] lg:leading-[1.08]"
          >
            {t("landing.hero.title")}
          </h1>
          <p className="max-w-xl animate-rise text-lg text-pretty text-ink-muted [animation-delay:160ms] lg:max-w-lg">
            {t("landing.hero.subtitle")}
          </p>
          <div className="flex animate-rise flex-col gap-3 [animation-delay:240ms] sm:flex-row">
            <MagneticButton className="sm:w-auto">
              <ButtonLink
                href={LOGIN_PATH}
                size="lg"
                fullWidth
                trailingIcon={<IconArrowRight className="size-4" aria-hidden />}
              >
                {t("landing.hero.primary")}
              </ButtonLink>
            </MagneticButton>
            <ButtonLink href="#pricing" size="lg" variant="secondary">
              {t("landing.hero.secondary")}
            </ButtonLink>
          </div>
          <p className="animate-rise text-sm text-pretty text-ink-subtle [animation-delay:320ms] lg:max-w-lg">
            {trialDays ? `${t("landing.hero.trial", { days: trialDays })} · ` : null}
            {t("landing.hero.note")}
          </p>
        </div>
        <HeroVisual
          label={t("landing.hero.sceneLabel")}
          className="mx-auto max-w-[22rem] animate-rise [animation-delay:200ms] sm:max-w-[30rem] lg:max-w-[34rem]"
        />
      </div>
    </section>
  );
}
