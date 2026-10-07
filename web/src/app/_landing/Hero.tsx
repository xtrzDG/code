import type { Schema } from "@/api/types";
import { IconArrowRight } from "@/components/icons";
import { MagneticButton } from "@/components/siteMotion";
import { ButtonLink } from "@/components/ui";
import type { Translator } from "@/i18n/translate";
import { CREATE_PATH } from "@/lib/navigation";

import { CabinetButtonLink } from "./CabinetLink";
import { DemoChat } from "./DemoChat";
import { DemoSample } from "./DemoSample";
import { HeroBackdrop } from "./HeroBackdrop";
import { HeroVisual } from "./HeroVisual";

type DemoList = Schema<"PublicDemoList">;

/**
 * What the product does and the two calls to action, beside a live demo
 * assistant the visitor can talk to right away (an example conversation
 * when no demo can answer). The assistant's picture glows behind the chat:
 * a CSS poster from the server, and on a capable wide screen the 3D scene
 * once the page is idle (HeroVisual); on a phone the poster rises above the
 * chat. The text moves in with CSS from the first paint, before any
 * script; the lead only lifts and the headline's gradient
 * sweeps (neither fades), so the largest text is painted with the first
 * frame.
 */
export function Hero({
  t,
  trialDays,
  demos,
}: {
  t: Translator["t"];
  trialDays: number | null;
  demos: DemoList | null;
}) {
  const liveDemos = demos?.demos ?? [];
  return (
    <section aria-labelledby="hero-title" className="relative isolate overflow-x-clip">
      <div className="relative mx-auto grid w-full max-w-6xl items-center gap-10 px-4 pt-12 pb-14 sm:px-6 sm:pt-20 sm:pb-20 grid-cols-[minmax(0,1fr)] lg:grid-cols-[minmax(0,1.1fr)_minmax(0,1fr)] lg:gap-12">
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
            className="landing-gradient-text animate-sheen text-4xl font-semibold tracking-tight text-balance [animation-delay:80ms] sm:text-5xl lg:max-w-[34rem] lg:leading-[1.08]"
          >
            {t("landing.hero.title")}
          </h1>
          <p className="max-w-xl animate-lift text-lg text-pretty text-ink-muted [animation-delay:160ms] lg:max-w-lg">
            {t("landing.hero.subtitle")}
          </p>
          <div className="flex animate-rise flex-col gap-3 [animation-delay:240ms] sm:flex-row">
            <MagneticButton className="sm:w-auto">
              <CabinetButtonLink
                href={CREATE_PATH}
                size="lg"
                fullWidth
                trailingIcon={<IconArrowRight className="size-4 rtl:-scale-x-100" aria-hidden />}
              >
                {t("landing.hero.primary")}
              </CabinetButtonLink>
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
        <div className="relative mx-auto w-full max-w-md animate-rise pt-36 [animation-delay:200ms] lg:max-w-none lg:pt-0">
          <div className="pointer-events-none absolute inset-x-0 -top-6 -z-10 mx-auto w-[19rem] lg:inset-x-auto lg:-top-20 lg:-end-28 lg:mx-0 lg:w-[30rem] lg:opacity-80">
            <HeroVisual label={t("landing.hero.sceneLabel")} />
          </div>
          <div id="demo" className="scroll-mt-20 overflow-hidden rounded-2xl border border-line bg-surface/95 shadow-2xl backdrop-blur">
            {liveDemos.length > 0 && demos ? (
              <DemoChat demos={liveDemos} messagesPerHour={demos.messages_per_hour} />
            ) : (
              <DemoSample t={t} />
            )}
          </div>
        </div>
      </div>
      <HeroBackdrop />
    </section>
  );
}
