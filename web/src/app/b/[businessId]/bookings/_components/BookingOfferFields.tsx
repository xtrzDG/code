"use client";

import type { KnowledgeItemDetails } from "@/api/types";
import { useBusinessFormat } from "@/components/business/BusinessContext";
import { todayIn } from "@/components/insights/dates";
import type { ResourceView } from "@/components/insights/types";
import { Alert, DateField, Field, Input, Select } from "@/components/ui";
import { useI18n } from "@/i18n/client";
import { BOOKABLE_KINDS } from "@/lib/offers";

import { KIND_GROUP_LABELS } from "../../assistant/knowledge/_components/hooks";
import { offerPickerKind } from "../_lib/bookingOffers";
import type { BookingFormErrors, BookingFormValues } from "../_lib/manualBooking";

/**
 * What is booked: the service, package or room type (when the business
 * has any), the date, how many people and the place. A chosen offer
 * narrows the places to those that perform it.
 */
export function BookingOfferFields({
  values,
  errors,
  offers,
  places,
  partyLabel,
  placeLabel,
  set,
  onOffer,
}: {
  values: BookingFormValues;
  errors: BookingFormErrors;
  /** Active offers, by kind and title. */
  offers: readonly KnowledgeItemDetails[];
  /** The places that may take the booking (the offer's performers when one is chosen). */
  places: readonly ResourceView[];
  partyLabel: string;
  placeLabel: string;
  set: <Key extends keyof BookingFormValues>(key: Key, value: BookingFormValues[Key]) => void;
  onOffer: (offerId: string) => void;
}) {
  const { t } = useI18n();
  const format = useBusinessFormat();
  const pickerKind = offerPickerKind(offers);
  const kinds = BOOKABLE_KINDS.filter((kind) => offers.some((offer) => offer.kind === kind));
  const optionLabel = (offer: KnowledgeItemDetails) =>
    [
      offer.title,
      offer.duration_minutes ? t("knowledge.items.minutes", { count: offer.duration_minutes }) : null,
      offer.price_minor !== null && offer.price_minor !== undefined
        ? offer.kind === "room_type"
          ? t("knowledge.offer.perNight", { price: format.money(offer.price_minor, offer.currency_code ?? undefined) })
          : format.money(offer.price_minor, offer.currency_code ?? undefined)
        : null,
    ]
      .filter(Boolean)
      .join(" · ");
  const options = (list: readonly KnowledgeItemDetails[]) =>
    list.map((offer) => (
      <option key={offer.id} value={offer.id}>
        {optionLabel(offer)}
      </option>
    ));
  const isFiltered = Boolean(values.serviceId);
  const chosenKind = offers.find((offer) => offer.id === values.serviceId)?.kind;

  return (
    <>
      {offers.length > 0 ? (
        <Field label={t(pickerKind === "roomType" ? "bookings.form.roomType" : "bookings.form.service")}>
          {(control) => (
            <Select {...control} value={values.serviceId} onChange={(event) => onOffer(event.target.value)}>
              <option value="">{t(pickerKind === "roomType" ? "bookings.form.anyRoomType" : "bookings.form.noService")}</option>
              {kinds.length > 1
                ? kinds.map((kind) => (
                    <optgroup key={kind} label={t(KIND_GROUP_LABELS[kind])}>
                      {options(offers.filter((offer) => offer.kind === kind))}
                    </optgroup>
                  ))
                : options(offers)}
            </Select>
          )}
        </Field>
      ) : null}

      <div className="grid gap-4 sm:grid-cols-3">
        <Field label={t("bookings.form.date")} error={errors.date && t(errors.date)} required>
          {(control) => (
            <DateField {...control} value={values.date} today={todayIn(format.timeZone)} onChange={(date) => set("date", date)} />
          )}
        </Field>
        <Field label={partyLabel} error={errors.partySize && t(errors.partySize)} required>
          {(control) => (
            <Input
              {...control}
              type="number"
              inputMode="numeric"
              min={1}
              max={10000}
              value={values.partySize}
              onChange={(event) => set("partySize", event.target.value)}
            />
          )}
        </Field>
        <Field
          label={placeLabel}
          hint={
            isFiltered && places.length > 0
              ? t(chosenKind === "room_type" ? "bookings.form.roomsOnly" : "bookings.form.performersOnly")
              : undefined
          }
        >
          {(control) => (
            <Select {...control} value={values.resourceId} onChange={(event) => set("resourceId", event.target.value)}>
              <option value="">{t("bookings.form.anyResource")}</option>
              {places.map((resource) => (
                <option key={resource.id} value={resource.id}>
                  {resource.name}
                </option>
              ))}
            </Select>
          )}
        </Field>
      </div>
      {isFiltered && places.length === 0 ? <Alert tone="warning">{t("bookings.form.noPerformers")}</Alert> : null}
    </>
  );
}
