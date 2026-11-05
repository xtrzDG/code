"use client";

/**
 * /create: "Create an AI assistant" for a business that does not exist
 * yet. The first two screens of the tunnel (what the business is, where it
 * is); the rest goes on at /b/{id}/setup once it is created. The draft is
 * read from this browser, so the screens wait for the browser before they
 * draw (no flash of empty fields).
 */

import { LoadingRegion, SkeletonText } from "@/components/ui";
import { useIsClient } from "@/components/workspace/useIsClient";
import type { CurrentUserView } from "@/api/types";
import { useI18n } from "@/i18n/client";
import { HOME_PATH } from "@/lib/navigation";
import type { RailState, TunnelPlace, TunnelStep } from "@/lib/tunnel/steps";

import { BusinessStep } from "../steps/BusinessStep";
import { PlaceStep } from "../steps/PlaceStep";
import { SaveTrackerProvider } from "../SaveTracker";
import { TunnelFrame } from "../TunnelFrame";
import { useTunnelPlace } from "../useTunnelPlace";
import { useCreateFlow } from "./useCreateFlow";

const NOT_YET: Record<TunnelStep, RailState> = {
  business: "todo",
  place: "todo",
  offer: "todo",
  hours: "todo",
  people: "todo",
  channels: "todo",
  try: "todo",
  launch: "todo",
};

function CreateFlow({ me }: { me: CurrentUserView }) {
  const { t } = useI18n();
  const flow = useCreateFlow(me);
  const { draft, setDraft } = flow;
  const hasBusiness = draft.name.trim() !== "" && draft.nicheKey !== "";
  const { place, direction, go } = useTunnelPlace(draft.step === "place" && hasBusiness ? "place" : "business", (candidate) =>
    candidate === "business" || (candidate === "place" && hasBusiness),
  );
  const hasOtherBusinesses = (me.memberships ?? []).length > 0;
  const states: Record<TunnelStep, RailState> = { ...NOT_YET, business: hasBusiness ? "done" : "todo" };

  const open = (next: TunnelPlace) => {
    if (next === "business" || next === "place") {
      setDraft((current) => ({ ...current, step: next }));
      go(next);
    }
  };

  return (
    <SaveTrackerProvider>
      {(saveState) => (
        <TunnelFrame
          place={place}
          direction={direction}
          states={states}
          canOpen={(step) => step === "business" || (step === "place" && hasBusiness)}
          onOpen={open}
          saveState={saveState}
          exitHref={hasOtherBusinesses ? HOME_PATH : null}
          homeHref={HOME_PATH}
        >
          {place === "place" ? (
            <PlaceStep
              form={draft}
              onChange={(form) => setDraft((current) => ({ ...current, ...form }))}
              place={flow.place}
              isCountryFixed={false}
              isAddressRequired={flow.niche?.takes_bookings ?? false}
              onBack={() => open("business")}
              onSubmit={() => void flow.finish()}
              isBusy={flow.isFinishing}
              busyLabel={t("tunnelBusiness.place.creating")}
            />
          ) : (
            <BusinessStep
              form={draft}
              onChange={(form) => setDraft((current) => ({ ...current, ...form }))}
              niches={{ data: flow.niches.data?.niches, error: flow.niches.error, reload: flow.niches.reload }}
              questions={flow.questions}
              isNicheFixed={false}
              onSubmit={() => open("place")}
            />
          )}
        </TunnelFrame>
      )}
    </SaveTrackerProvider>
  );
}

export function CreateTunnel({ me }: { me: CurrentUserView }) {
  const { t } = useI18n();
  const isClient = useIsClient();
  if (!isClient) {
    return (
      <div className="mx-auto flex min-h-dvh max-w-2xl items-center px-4">
        <LoadingRegion label={t("common.loading")} className="w-full">
          <SkeletonText lines={4} />
        </LoadingRegion>
      </div>
    );
  }
  return <CreateFlow me={me} />;
}
