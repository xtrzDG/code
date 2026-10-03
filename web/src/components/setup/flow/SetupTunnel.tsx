"use client";

/**
 * /b/{id}/setup: the tunnel of a business that exists, from what it offers
 * to the launch and the finale (its first two steps can be changed here
 * too). It opens where the owner left off (or at `?step=`), reads the
 * guided setup, the niche's starter answers and the profile first, and
 * hands every screen the same moves (on, back, to a step, skip for now).
 */

import { useCallback, useMemo, useState, type ReactNode } from "react";

import { api } from "@/api/client";
import { unwrap } from "@/api/result";
import type { ProfileWizardView, Schema } from "@/api/types";
import { useBusiness } from "@/components/business/BusinessContext";
import { ButtonLink, ErrorState, LoadingRegion, SkeletonText, useToast } from "@/components/ui";
import { describeError } from "@/api/errors";
import { useI18n } from "@/i18n/client";
import { businessPath, HOME_PATH } from "@/lib/navigation";
import { nextPlace, previousStep, resumePlace, SKIPPABLE_STEPS, stepStates, type TunnelPlace, type TunnelStep } from "@/lib/tunnel/steps";

import { ChannelsScreen } from "../channels/ChannelsScreen";
import { FinaleScreen } from "../finale/FinaleScreen";
import { HoursScreen } from "../hours/HoursScreen";
import { LaunchScreen } from "../launch/LaunchScreen";
import { OfferScreen } from "../offer/OfferScreen";
import { PeopleScreen } from "../people/PeopleScreen";
import { TryScreen } from "../try/TryScreen";
import { SaveTrackerProvider } from "../SaveTracker";
import { TunnelFrame } from "../TunnelFrame";
import { useTunnelPlace } from "../useTunnelPlace";
import { BusinessScreen } from "./BusinessScreen";
import { PlaceScreen } from "./PlaceScreen";
import type { StepContext } from "./stepContext";
import { useSetupData } from "./useSetupData";

const SCREENS: Record<TunnelPlace, (props: { ctx: StepContext }) => ReactNode> = {
  business: BusinessScreen,
  place: PlaceScreen,
  offer: OfferScreen,
  hours: HoursScreen,
  people: PeopleScreen,
  channels: ChannelsScreen,
  try: TryScreen,
  launch: LaunchScreen,
  done: FinaleScreen,
};

interface Loaded {
  setup: Schema<"SetupView">;
  starters: Schema<"StarterAnswersView">;
  wizard: ProfileWizardView;
}

function SetupFlow({ businessId, data, refresh }: { businessId: string; data: Loaded; refresh: () => void }) {
  const { t } = useI18n();
  const toast = useToast();
  const { setup } = data;
  const [start] = useState(() => resumePlace(setup));
  const [hasLaunched, setLaunched] = useState(false);
  const { place, direction, go } = useTunnelPlace(start, (candidate) => candidate !== "done" || setup.is_live || hasLaunched);

  const goTo = useCallback(
    (next: TunnelPlace) => {
      if (next === "done") {
        setLaunched(true);
      }
      go(next);
    },
    [go],
  );

  const skip = useCallback(
    async (step: TunnelStep) => {
      const code = SKIPPABLE_STEPS[step];
      if (code) {
        try {
          await unwrap(
            api.PUT("/v1/businesses/{business_id}/setup/skipped-steps/{setup_step}", {
              params: { path: { business_id: businessId, setup_step: code } },
            }),
          );
          refresh();
        } catch (error) {
          toast.show({ tone: "error", title: describeError(error, t).title });
          return;
        }
      }
      goTo(nextPlace(step));
    },
    [businessId, goTo, refresh, t, toast],
  );

  const ctx = useMemo<StepContext>(
    () => ({
      businessId,
      ...data,
      refresh,
      next: () => goTo(place === "done" ? "done" : nextPlace(place)),
      back: () => {
        const previous = previousStep(place);
        if (previous) {
          goTo(previous);
        }
      },
      goTo,
      skip,
    }),
    [businessId, data, refresh, goTo, skip, place],
  );

  const Screen = SCREENS[place];
  return (
    <SaveTrackerProvider>
      {(saveState) => (
        <TunnelFrame
          place={place}
          direction={direction}
          states={stepStates(setup)}
          canOpen={() => true}
          onOpen={goTo}
          saveState={saveState}
          exitHref={businessPath(businessId, "overview")}
          homeHref={HOME_PATH}
        >
          <Screen ctx={ctx} />
        </TunnelFrame>
      )}
    </SaveTrackerProvider>
  );
}

function Centered({ children }: { children: ReactNode }) {
  return <div className="mx-auto flex min-h-dvh w-full max-w-xl flex-col justify-center px-4 py-10">{children}</div>;
}

export function SetupTunnel() {
  const { t } = useI18n();
  const { business, isOwner, isPlatformAdmin } = useBusiness();
  const canSetUp = isOwner || isPlatformAdmin;
  const data = useSetupData(business.id, canSetUp);
  const { setup, starters, wizard } = data;

  if (!canSetUp) {
    return (
      <Centered>
        <h1 className="text-2xl font-semibold text-ink">{t("tunnel.ownerOnlyTitle")}</h1>
        <p className="mt-3 text-ink-muted">{t("tunnel.ownerOnlyText")}</p>
        <ButtonLink href={businessPath(business.id, "overview")} className="mt-6 self-start">
          {t("tunnel.openCabinet")}
        </ButtonLink>
      </Centered>
    );
  }

  const error = (!setup.data && setup.error) || (!starters.data && starters.error) || (!wizard.data && wizard.error);
  if (error) {
    const retry = () => {
      setup.reload();
      starters.reload();
      wizard.reload();
    };
    return (
      <Centered>
        <ErrorState error={error} onRetry={retry} />
      </Centered>
    );
  }
  if (!setup.data || !starters.data || !wizard.data) {
    return (
      <Centered>
        <LoadingRegion label={t("common.loading")}>
          <SkeletonText lines={5} />
        </LoadingRegion>
      </Centered>
    );
  }
  return <SetupFlow businessId={business.id} data={{ setup: setup.data, starters: starters.data, wizard: wizard.data }} refresh={data.refresh} />;
}
