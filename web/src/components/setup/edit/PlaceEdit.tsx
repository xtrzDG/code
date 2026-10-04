"use client";

/**
 * "Place" in Assistant → Business profile: the second screen of the
 * tunnel in the edit mode. The city, languages and time zone (the
 * business's own settings), the address with its map link, the phone for
 * customers and the language of the owner's answers (the profile), each
 * saved by itself as the owner types.
 */

import { useState } from "react";

import { useNiches } from "@/api/catalog";
import { useBusiness } from "@/components/business/BusinessContext";
import { Field, Input, Select } from "@/components/ui";
import { useI18n } from "@/i18n/client";
import { languageName } from "@/lib/format";
import { webLinkSchema } from "@/lib/validation";

import { useBusinessSave } from "../flow/useBusinessSave";
import type { StepContext } from "../flow/stepContext";
import { PlaceStep } from "../steps/PlaceStep";
import { usePlace, type PlaceForm } from "../usePlace";
import { PhoneField } from "./PhoneField";
import { SaveProblem } from "./SaveProblem";
import { useBusinessField } from "./useBusinessField";
import { useProfileField } from "./useProfileField";

export function PlaceEdit({ ctx }: { ctx: StepContext }) {
  const { t, locale } = useI18n();
  const { business, me } = useBusiness();
  const niches = useNiches();
  const takesBookings = niches.data?.niches.find((niche) => niche.key === business.niche_key)?.takes_bookings ?? false;
  const { profile } = ctx.wizard;
  const country = business.country_code;
  const [form, setForm] = useState<PlaceForm>(() => ({
    countryCode: country,
    city: business.city ?? "",
    address: profile.address?.text ?? "",
    languagesByCountry: { [country]: business.languages },
    defaultByCountry: { [country]: business.default_language },
    zoneByCountry: { [country]: business.timezone },
  }));
  const [mapsUrl, setMapsUrl] = useState(profile.address?.maps_url ?? "");
  const [publicPhone, setPublicPhone] = useState(profile.contacts.public_phone_number ?? "");
  const [answersLanguage, setAnswersLanguage] = useState(profile.answers_language);
  const place = usePlace(form, me.user.country_code);
  const businessSave = useBusinessSave(ctx.businessId);

  const settings = { city: form.city.trim(), languages: place.languages, defaultLanguage: place.defaultLanguage, timezone: place.timezone };
  useBusinessField(
    businessSave,
    settings,
    (value) => ({
      city: value.city,
      languages: value.languages,
      ...(value.defaultLanguage ? { default_language: value.defaultLanguage } : {}),
      ...(value.timezone ? { timezone: value.timezone } : {}),
    }),
    { enabled: Boolean(place.defaults), isValid: (value) => value.languages.length > 0 },
  );

  const address = form.address.trim();
  const maps = mapsUrl.trim();
  const mapsProblem = maps === "" ? null : !webLinkSchema.safeParse(maps).success ? t("validation.url") : address === "" ? t("profileEdit.place.mapsNeedsAddress") : null;
  const addressMissing = takesBookings && address === "";
  const addressSave = useProfileField(
    ctx.businessId,
    address ? { text: address, maps_url: maps || null } : null,
    (value) => ({ address: value }),
    { isValid: () => mapsProblem === null && !addressMissing },
  );
  const phoneSave = useProfileField(ctx.businessId, publicPhone.trim(), (value) => ({ contacts: { public_phone_number: value || null } }));
  const languageSave = useProfileField(ctx.businessId, answersLanguage, (value) => ({ answers_language: value }));
  const answerLanguages = [...new Set([profile.answers_language, business.owner_language, ...place.languages])];

  return (
    <PlaceStep
      mode="edit"
      form={form}
      onChange={setForm}
      place={place}
      isCountryFixed
      isAddressRequired={takesBookings}
      onBack={() => undefined}
      onSubmit={() => undefined}
      problems={{ languages: place.languages.length === 0, address: addressMissing }}
      extra={
        <div className="space-y-6">
          <Field label={t("profileEdit.place.mapsUrl")} hint={t("profileEdit.place.mapsUrlHint")} optionalLabel={t("common.optional")} error={mapsProblem ?? undefined}>
            {(control) => (
              <Input {...control} type="url" inputMode="url" dir="ltr" maxLength={2048} placeholder="https://" value={mapsUrl} onChange={(event) => setMapsUrl(event.target.value)} />
            )}
          </Field>
          <SaveProblem error={addressSave.error} />
          <div className="grid gap-6 sm:grid-cols-2">
            <PhoneField
              label={t("profileEdit.place.publicPhone")}
              hint={t("profileEdit.place.publicPhoneHint")}
              value={publicPhone}
              onChange={setPublicPhone}
              error={phoneSave.error}
            />
            <Field label={t("profileEdit.place.answersLanguage")} hint={t("profileEdit.place.answersLanguageHint")} error={languageSave.error ? t("tunnel.saveFailed") : undefined}>
              {(control) => (
                <Select {...control} value={answersLanguage} onChange={(event) => setAnswersLanguage(event.target.value)}>
                  {answerLanguages.map((tag) => (
                    <option key={tag} value={tag}>
                      {languageName(tag, locale)}
                    </option>
                  ))}
                </Select>
              )}
            </Field>
          </div>
        </div>
      }
    />
  );
}
