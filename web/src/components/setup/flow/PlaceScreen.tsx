"use client";

/**
 * Step 2 for a business that exists: its country (fixed), city, languages
 * and time zone (saved on Continue) and the address (saved by itself a
 * moment after it is typed).
 */

import { useState } from "react";

import { useNiches } from "@/api/catalog";
import { useBusiness } from "@/components/business/BusinessContext";

import { PlaceStep } from "../steps/PlaceStep";
import { useAutosave } from "../useAutosave";
import { usePlace, type PlaceForm } from "../usePlace";
import type { StepContext } from "./stepContext";
import { useBusinessSave } from "./useBusinessSave";
import { useProfilePatch } from "./useProfilePatch";

export function PlaceScreen({ ctx }: { ctx: StepContext }) {
  const { business, me } = useBusiness();
  const niches = useNiches();
  const takesBookings = niches.data?.niches.find((niche) => niche.key === business.niche_key)?.takes_bookings ?? false;
  const country = business.country_code;
  const [form, setForm] = useState<PlaceForm>(() => ({
    countryCode: country,
    city: business.city ?? "",
    address: ctx.wizard.profile.address?.text ?? "",
    languagesByCountry: { [country]: business.languages },
    defaultByCountry: { [country]: business.default_language },
    zoneByCountry: { [country]: business.timezone },
  }));
  const place = usePlace(form, me.user.country_code);

  const patchProfile = useProfilePatch(ctx.businessId);
  const address = form.address.trim();
  const autosave = useAutosave(address, (text) => patchProfile({ address: text ? { text } : null }));
  const businessSave = useBusinessSave(ctx.businessId);
  const [isSaving, setSaving] = useState(false);

  const submit = async () => {
    setSaving(true);
    const savedAddress = await autosave.flush();
    const saved = await businessSave.save(() => ({
      city: form.city.trim(),
      languages: place.languages,
      ...(place.defaultLanguage ? { default_language: place.defaultLanguage } : {}),
      ...(place.timezone ? { timezone: place.timezone } : {}),
    }));
    setSaving(false);
    if (savedAddress && saved) {
      ctx.refresh();
      ctx.next();
    }
  };

  return (
    <PlaceStep
      form={form}
      onChange={setForm}
      place={place}
      isCountryFixed
      isAddressRequired={takesBookings}
      onBack={ctx.back}
      onSubmit={() => void submit()}
      isBusy={isSaving}
    />
  );
}
