"use client";

/**
 * What every section shows before the assistant exists: one big invitation
 * to create it. The assistant's orb floats among its channels in a tilting
 * card, a floor of light runs towards the viewer (the "tunnel" the setup
 * leads through), and one button starts the flow; progress shows once a
 * step is done. Staff read that the owner is setting it up.
 */

import { HeroFallback } from "@/app/_landing/HeroFallback";
import { api } from "@/api/client";
import { queryKeys } from "@/api/queryKeys";
import { useQuery } from "@/api/useQuery";
import { useBusiness } from "@/components/business/BusinessContext";
import { IconArrowRight, IconClock } from "@/components/icons";
import { FadeIn, MagneticButton, TiltCard } from "@/components/motion";
import { ButtonLink } from "@/components/ui";
import { useI18n } from "@/i18n/client";
import { setupPath } from "@/lib/navigation";
import { stepStates, TUNNEL_STEPS } from "@/lib/tunnel/steps";

import { SetupStages } from "./SetupStages";

/** How far the owner got in the tunnel (its eight steps), once the guided setup answered. */
function useSetupProgress(businessId: string, canSetUp: boolean): { done: number; total: number } | null {
  const { locale } = useI18n();
  const setup = useQuery(
    queryKeys.setup.progress(businessId, locale),
    () => api.GET("/v1/businesses/{business_id}/setup", { params: { path: { business_id: businessId }, query: { language: locale } } }),
    { enabled: canSetUp },
  );
  if (!setup.data) {
    return null;
  }
  const states = Object.values(stepStates(setup.data));
  return { done: states.filter((state) => state === "done").length, total: TUNNEL_STEPS.length };
}

export function SetupHero({ canSetUp }: { canSetUp: boolean }) {
  const { t } = useI18n();
  const { business } = useBusiness();
  const progress = useSetupProgress(business.id, canSetUp);
  const hasStarted = progress !== null && progress.done > 0;

  return (
    <section className="relative isolate overflow-hidden rounded-3xl border border-line bg-surface px-5 py-8 sm:px-10 sm:py-12">
      <div aria-hidden className="landing-aurora -z-10">
        <span />
        <span />
        <span />
      </div>
      <div aria-hidden className="landing-floor -z-10">
        <div className="landing-floor-plane">
          <span />
        </div>
      </div>

      <div className="grid items-center gap-8 lg:grid-cols-[minmax(0,1.1fr)_minmax(0,1fr)]">
        <FadeIn tone="landing">
          <p className="text-sm font-medium text-accent">{t("setup.eyebrow", { business: business.name })}</p>
          <h1 className="mt-2 text-3xl font-semibold tracking-tight text-balance text-ink sm:text-4xl">
            {canSetUp ? t("setup.title") : t("setup.staffTitle")}
          </h1>
          <p className="mt-4 max-w-xl text-base text-ink-muted">
            {canSetUp ? t("setup.description") : t("setup.staffDescription", { business: business.name })}
          </p>

          {progress && hasStarted ? (
            <div className="mt-6 max-w-sm">
              <p className="text-sm font-medium text-ink">{t("setup.progress", { done: progress.done, total: progress.total })}</p>
              <div
                role="progressbar"
                aria-valuemin={0}
                aria-valuemax={progress.total}
                aria-valuenow={progress.done}
                aria-label={t("setup.progress", { done: progress.done, total: progress.total })}
                className="mt-2 h-2 overflow-hidden rounded-full bg-surface-muted"
              >
                <div
                  className="h-full rounded-full bg-accent-solid transition-[width] duration-(--motion-slow)"
                  style={{ width: `${Math.round((progress.done / progress.total) * 100)}%` }}
                />
              </div>
            </div>
          ) : null}

          {canSetUp ? (
            <div className="mt-8 flex flex-col items-start gap-3">
              <MagneticButton>
                <ButtonLink
                  href={setupPath(business.id)}
                  size="lg"
                  className="h-12 px-6 text-base shadow-[0_18px_40px_-16px_var(--accent-solid)]"
                  trailingIcon={<IconArrowRight className="size-5 rtl:-scale-x-100" aria-hidden />}
                >
                  {hasStarted ? t("setup.continue") : t("setup.start")}
                </ButtonLink>
              </MagneticButton>
              <p className="flex items-center gap-1.5 text-xs text-ink-subtle">
                <IconClock className="size-3.5" aria-hidden />
                {t("setup.duration")}
              </p>
            </div>
          ) : null}
        </FadeIn>

        <TiltCard className="relative mx-auto aspect-square w-full max-w-[22rem] sm:max-w-sm">
          <HeroFallback />
        </TiltCard>
      </div>

      {canSetUp ? (
        <div className="mt-10">
          <SetupStages />
        </div>
      ) : null}
    </section>
  );
}
