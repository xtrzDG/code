"use client";

import Link from "next/link";
import { useState, type FormEvent } from "react";

import { useNiche } from "@/api/catalog";
import { api } from "@/api/client";
import { useBookableOffers } from "@/api/offers";
import { useMutation } from "@/api/useMutation";
import { useBusiness } from "@/components/business/BusinessContext";
import { CHANNEL_LABELS, CUSTOMER_CHANNELS } from "@/components/insights/labels";
import type { BookingResult, ChannelKind, ManualBookingBody, ResourceView } from "@/components/insights/types";
import { usePartyWording } from "@/components/insights/usePartyWording";
import { Alert, Button, Field, Select, Textarea } from "@/components/ui";
import { useI18n } from "@/i18n/client";
import { capitalizeFirst } from "@/lib/format";
import { businessPath } from "@/lib/navigation";
import { bookingValue, sortOffers } from "@/lib/offers";

import { bookedOffer, placesForOffer, withOffer } from "../_lib/bookingOffers";
import { BOOKING_REFUSAL_MESSAGES } from "../_lib/bookingRefusals";
import { bookingUnitFor, validateBookingForm, type BookingFormErrors, type BookingFormValues } from "../_lib/manualBooking";
import { BookingCustomerFields } from "./BookingCustomerFields";
import { BookingOfferFields } from "./BookingOfferFields";
import { BookingTimingFields } from "./BookingTimingFields";
import { BookingValueLine } from "./BookingValueLine";
import { CustomerLanguageSelect } from "./CustomerLanguageSelect";

/**
 * A booking taken by phone or in person (POST …/bookings). The API checks
 * opening hours and free places; "Show free times" offers slots first.
 * The phone is read in the chosen country (the business country first).
 * Choosing a service fills in its length, offers only those who perform
 * it and shows what the booking is worth. From a conversation card the
 * form is prefilled and the booking linked.
 */
export function BookingForm({
  resources,
  defaultDate,
  onCreated,
  onCancel,
  initialValues,
  conversationId,
}: {
  resources: readonly ResourceView[];
  defaultDate: string;
  onCreated: (result: BookingResult) => void;
  onCancel: () => void;
  initialValues?: Partial<BookingFormValues>;
  conversationId?: string;
}) {
  const { t, locale } = useI18n();
  const { business } = useBusiness();
  const businessId = business.id;
  const niche = useNiche(business.niche_key).data?.niche;
  const party = usePartyWording();
  const allOffers = useBookableOffers(businessId).data ?? [];
  const offers = sortOffers(allOffers, locale);
  const activeResources = resources.filter((resource) => resource.is_active);

  const [values, setValues] = useState<BookingFormValues>({
    contactName: "",
    phone: "",
    date: defaultDate,
    time: "",
    nights: "1",
    partySize: "",
    resourceId: "",
    serviceId: "",
    duration: "",
    notes: "",
    source: "phone",
    language: business.default_language,
    country: business.country_code,
    ...initialValues,
  });
  const [errors, setErrors] = useState<BookingFormErrors>({});
  // Until staff type a number, a booking is for 2 guests, or for 1 client or participant.
  const [isPartyTyped, setPartyTyped] = useState(initialValues?.partySize !== undefined);
  const form = isPartyTyped ? values : { ...values, partySize: party.noun(values.resourceId || null) === "guests" ? "2" : "1" };
  const chosenOffer = allOffers.find((offer) => offer.id === values.serviceId) ?? null;
  const unit = bookingUnitFor(resources, values.resourceId, chosenOffer);
  const places = placesForOffer(chosenOffer, resources, allOffers);
  const offer = bookedOffer(values, resources, allOffers);
  const nights = unit === "night" && /^\d+$/.test(values.nights) && Number(values.nights) > 0 ? Number(values.nights) : null;
  const value = bookingValue(offer, { date: values.date, nights }, business.currency_code);
  // A business booking one kind of resource names it ("Master", "Table"); a mixed one says "Place".
  const placeLabel =
    niche && activeResources.length > 0 && activeResources.every((resource) => resource.kind === niche.resource_kind)
      ? capitalizeFirst(niche.resource_noun, locale)
      : t("bookings.form.resource");

  const create = useMutation(
    (body: ManualBookingBody) =>
      api.POST("/v1/businesses/{business_id}/bookings", { params: { path: { business_id: businessId } }, body }),
    { errorMessages: { conflict: "bookings.errors.conflict" }, reasonMessages: BOOKING_REFUSAL_MESSAGES },
  );

  const set = <Key extends keyof BookingFormValues>(key: Key, value: BookingFormValues[Key]) => {
    if (key === "partySize") {
      setPartyTyped(true);
    }
    setValues((current) => ({ ...current, [key]: value }));
    setErrors((current) => ({ ...current, [key]: undefined }));
  };

  const chooseOffer = (offerId: string) => {
    const next = allOffers.find((item) => item.id === offerId) ?? null;
    setValues((current) => withOffer(current, next, resources, allOffers));
    setErrors((current) => ({ ...current, resourceId: undefined, duration: undefined }));
  };

  const submit = async (event: FormEvent) => {
    event.preventDefault();
    const result = validateBookingForm(form, unit, chosenOffer);
    if (!result.ok) {
      setErrors(result.errors);
      return;
    }
    const created = await create.run(conversationId ? { ...result.body, conversation_id: conversationId } : result.body);
    if (created.ok) {
      onCreated(created.data);
    }
  };

  return (
    <form onSubmit={submit} noValidate className="space-y-5">
      {activeResources.length === 0 ? (
        <Alert tone="info">
          <p>{t("bookings.form.noResources")}</p>
          <Link
            href={`${businessPath(businessId, "assistant/profile")}?step=booking_rules`}
            className="mt-1 inline-block font-medium text-accent hover:underline"
          >
            {t("bookings.form.toProfile")}
          </Link>
        </Alert>
      ) : null}
      <BookingCustomerFields values={form} errors={errors} set={set} />

      <BookingOfferFields
        values={form}
        errors={errors}
        offers={offers}
        places={places}
        partyLabel={party.label(values.resourceId || places[0]?.id)}
        placeLabel={placeLabel}
        set={set}
        onOffer={chooseOffer}
      />

      <BookingTimingFields
        values={form}
        errors={errors}
        unit={unit}
        usualDuration={chosenOffer?.duration_minutes ?? null}
        set={set}
        onPick={(slot) => {
          setValues((current) => ({
            ...current,
            time: slot.time ?? current.time,
            resourceId: slot.resource_id,
            nights: slot.nights ? String(slot.nights) : current.nights,
          }));
          setErrors((current) => ({ ...current, time: undefined, nights: undefined }));
        }}
      />

      <div className="grid gap-4 sm:grid-cols-2">
        <Field label={t("bookings.form.source")}>
          {(control) => (
            <Select {...control} value={values.source} onChange={(event) => set("source", event.target.value as ChannelKind)}>
              {CUSTOMER_CHANNELS.map((channel) => (
                <option key={channel} value={channel}>
                  {t(CHANNEL_LABELS[channel])}
                </option>
              ))}
            </Select>
          )}
        </Field>
        <CustomerLanguageSelect value={values.language} onChange={(language) => set("language", language)} />
      </div>

      <Field label={t("bookings.form.notes")} error={errors.notes && t(errors.notes)} optionalLabel={t("common.optional")}>
        {(control) => (
          <Textarea
            {...control}
            dir="auto"
            rows={2}
            maxLength={1000}
            placeholder={t("bookings.form.notesPlaceholder")}
            value={values.notes}
            onChange={(event) => set("notes", event.target.value)}
          />
        )}
      </Field>

      <BookingValueLine offer={offer} value={value} nights={nights} />

      <div className="flex flex-wrap justify-end gap-3 border-t border-line pt-4">
        <Button variant="secondary" onClick={onCancel} disabled={create.isPending}>
          {t("common.cancel")}
        </Button>
        <Button type="submit" isLoading={create.isPending} loadingText={t("bookings.form.submitting")}>
          {t("bookings.form.submit")}
        </Button>
      </div>
    </form>
  );
}
