"use client";

import Link from "next/link";

import { useBookableOffers } from "@/api/offers";
import type { KnowledgeItemDetails } from "@/api/types";
import { useBusiness, useBusinessFormat } from "@/components/business/BusinessContext";
import { Field, Select, Spinner } from "@/components/ui";
import { useI18n } from "@/i18n/client";
import { businessPath } from "@/lib/navigation";
import { kindHasBuffer, sortOffers } from "@/lib/offers";
import type { ResourceForm } from "@/lib/resources";

import { OptionChecklist, type ChecklistOption } from "../../_components/OptionChecklist";

/**
 * What a resource is linked to: the services and packages a master, bay or
 * arena performs (booked by time), or the room type of a room (booked by
 * the night). Switched-off offers it is linked to stay listed, marked off.
 */
export function ResourceOfferFields({
  form,
  change,
}: {
  form: ResourceForm;
  change: (patch: Partial<ResourceForm>) => void;
}) {
  const { t, locale } = useI18n();
  const { business } = useBusiness();
  const format = useBusinessFormat();
  const offers = useBookableOffers(business.id);
  const items = offers.data ?? [];
  const itemsLink = (
    <Link href={businessPath(business.id, "assistant/knowledge")} className="font-medium text-accent hover:underline">
      {t("knowledge.resources.toItems")}
    </Link>
  );

  if (offers.isLoading) {
    return <Spinner size="sm" label={t("common.loading")} className="text-ink-subtle" />;
  }

  if (form.bookingUnit === "night") {
    const roomTypes = [
      ...sortOffers(items, locale).filter((item) => item.kind === "room_type"),
      ...items.filter((item) => item.kind === "room_type" && !item.is_active && item.id === form.roomTypeId),
    ];
    if (roomTypes.length === 0 && form.kind !== "room") {
      return null;
    }
    return roomTypes.length === 0 ? (
      <p className="text-sm text-ink-muted">
        {t("knowledge.resources.noRoomTypes")} {itemsLink}
      </p>
    ) : (
      <Field label={t("knowledge.resources.roomType")} hint={t("knowledge.resources.roomTypeHint")} className="sm:max-w-sm">
        {(control) => (
          <Select {...control} value={form.roomTypeId} onChange={(event) => change({ roomTypeId: event.target.value })}>
            <option value="">{t("knowledge.resources.roomTypeNone")}</option>
            {roomTypes.map((item) => (
              <option key={item.id} value={item.id}>
                {item.is_active ? item.title : `${item.title} (${t("knowledge.offer.resourceOff")})`}
              </option>
            ))}
          </Select>
        )}
      </Field>
    );
  }

  const options = serviceOptions(items, form.serviceIds, locale, (item) =>
    [
      item.duration_minutes ? t("knowledge.items.minutes", { count: item.duration_minutes }) : null,
      item.price_minor !== null && item.price_minor !== undefined ? format.money(item.price_minor, item.currency_code ?? undefined) : null,
    ]
      .filter((part): part is string => part !== null)
      .join(" · "),
  );
  // Tables and halls rarely perform services: say nothing until the business has some.
  if (options.length === 0 && (form.kind === "table" || form.kind === "room")) {
    return null;
  }
  return (
    <OptionChecklist
      legend={t("knowledge.resources.services")}
      hint={options.length > 0 ? t("knowledge.resources.servicesHint") : undefined}
      options={options}
      selected={form.serviceIds}
      onChange={(serviceIds) => change({ serviceIds })}
      empty={
        <p className="text-sm text-ink-muted">
          {t("knowledge.resources.noServices")} {itemsLink}
        </p>
      }
    />
  );
}

/** Active services and packages, then switched-off ones the resource is still linked to. */
function serviceOptions(
  items: readonly KnowledgeItemDetails[],
  linked: readonly string[],
  locale: string,
  note: (item: KnowledgeItemDetails) => string,
): ChecklistOption[] {
  const services = items.filter((item) => kindHasBuffer(item.kind));
  const active = sortOffers(services, locale);
  const off = services.filter((item) => !item.is_active && linked.includes(item.id));
  return [...active, ...off].map((item) => ({ id: item.id, label: item.title, note: note(item) || undefined, isOff: !item.is_active }));
}
