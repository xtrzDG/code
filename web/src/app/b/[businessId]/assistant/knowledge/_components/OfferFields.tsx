"use client";

import Link from "next/link";

import { api } from "@/api/client";
import { queryKeys } from "@/api/queryKeys";
import { useQuery } from "@/api/useQuery";
import { useBusiness } from "@/components/business/BusinessContext";
import { Spinner } from "@/components/ui";
import { useI18n } from "@/i18n/client";
import type { KnowledgeForm, KnowledgeFormErrors } from "@/lib/knowledge/form";
import { businessPath } from "@/lib/navigation";
import { offerBookingUnit } from "@/lib/offers";
import { sortResources, type ResourceView } from "@/lib/resources";

import { RESOURCE_KIND_LABELS } from "../resources/ResourceEditor";
import { OptionChecklist, type ChecklistOption } from "./OptionChecklist";
import { SeasonalRatesEditor } from "./SeasonalRatesEditor";

/**
 * The bookable part of the item editor: who performs a service or package
 * (or which rooms are of a room type), and a room type's seasonal rates.
 * Only resources booked the offer's way are offered (by time for services,
 * by the night for room types), plus any already linked.
 */
export function OfferFields({
  form,
  errors,
  currency,
  change,
}: {
  form: KnowledgeForm;
  errors: KnowledgeFormErrors;
  currency: string;
  change: (patch: Partial<KnowledgeForm>) => void;
}) {
  const { t, locale } = useI18n();
  const { business } = useBusiness();
  const resources = useQuery(queryKeys.resources.list(business.id), () =>
    api.GET("/v1/businesses/{business_id}/resources", { params: { path: { business_id: business.id } } }),
  );
  const isRoomType = form.kind === "room_type";
  const options = performerOptions(sortResources(resources.data?.items ?? [], locale), form, (resource) =>
    t(RESOURCE_KIND_LABELS[resource.kind]),
  );

  return (
    <>
      <div className="sm:col-span-6">
        {resources.isLoading ? (
          <Spinner size="sm" label={t("common.loading")} className="text-ink-subtle" />
        ) : (
          <OptionChecklist
            legend={t(isRoomType ? "knowledge.offer.rooms" : "knowledge.offer.performers")}
            hint={options.length > 0 ? t(isRoomType ? "knowledge.offer.roomsHint" : "knowledge.offer.performersHint") : undefined}
            options={options}
            selected={form.performerIds}
            onChange={(performerIds) => change({ performerIds })}
            empty={
              <p className="text-sm text-ink-muted">
                {t(isRoomType ? "knowledge.offer.noRooms" : "knowledge.offer.noResources")}{" "}
                <Link href={`${businessPath(business.id, "assistant/knowledge")}/resources`} className="font-medium text-accent hover:underline">
                  {t("knowledge.offer.toResources")}
                </Link>
              </p>
            }
          />
        )}
      </div>
      {isRoomType ? (
        <div className="sm:col-span-6">
          <SeasonalRatesEditor
            rows={form.seasons}
            currency={currency}
            problem={errors.seasons}
            onChange={(seasons) => change({ seasons })}
          />
        </div>
      ) : null}
    </>
  );
}

/** The resources an offer may be linked to: those booked its way, and any it is linked to already. */
export function performerOptions(
  resources: readonly ResourceView[],
  form: Pick<KnowledgeForm, "kind" | "performerIds">,
  kindLabel: (resource: ResourceView) => string,
): ChecklistOption[] {
  const unit = offerBookingUnit(form.kind);
  return resources
    .filter((resource) => resource.booking_unit === unit || form.performerIds.includes(resource.id))
    .map((resource) => ({ id: resource.id, label: resource.name, note: kindLabel(resource), isOff: !resource.is_active }));
}
