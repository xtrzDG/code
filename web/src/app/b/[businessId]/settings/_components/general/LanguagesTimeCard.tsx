"use client";

import { Card, Checkbox, Field, Fieldset, Select } from "@/components/ui";
import { useBusiness } from "@/components/business/BusinessContext";
import { useI18n } from "@/i18n/client";
import { capitalizeFirst } from "@/lib/format";
import { timeZoneLabel } from "@/lib/timeZones";

import { toggleLanguage } from "../../_lib/general";
import type { GeneralChoices } from "../../_lib/useGeneralChoices";
import type { GeneralSettings } from "../../_lib/useGeneralSettings";

/** Time zone, the customers' languages (and the default one) and the owner's language. */
export function LanguagesTimeCard({ settings, options }: { settings: GeneralSettings; options: GeneralChoices }) {
  const { t, locale } = useI18n();
  const { isOwner } = useBusiness();
  const { form, disabled, update, errorText } = settings;
  const { labelOf, choices, addable, ownerLanguages, countryZones, otherZones } = options;
  return (
    <Card title={t("settings.general.languagesTitle")}>
      <div className="space-y-6">
        <Field label={t("settings.general.timezone")} hint={t("settings.general.timezoneHint")}>
          {(control) => (
            <Select {...control} value={form.timezone} disabled={disabled} onChange={(event) => update("timezone", event.target.value)}>
              {countryZones.length > 0 ? (
                <optgroup label={t("settings.general.countryTimezones")}>
                  {countryZones.map((zone) => (
                    <option key={zone.name} value={zone.name}>
                      {timeZoneLabel(zone.name, locale)}
                    </option>
                  ))}
                </optgroup>
              ) : null}
              {!countryZones.some((zone) => zone.name === form.timezone) && !otherZones.includes(form.timezone) ? (
                <option value={form.timezone}>{timeZoneLabel(form.timezone, locale)}</option>
              ) : null}
              {otherZones.length > 0 ? (
                <optgroup label={t("settings.general.allTimezones")}>
                  {otherZones.map((zone) => (
                    <option key={zone} value={zone}>
                      {timeZoneLabel(zone, locale)}
                    </option>
                  ))}
                </optgroup>
              ) : null}
            </Select>
          )}
        </Field>

        <Fieldset legend={t("settings.general.languages")} hint={t("settings.general.languagesHint")} error={errorText("languages")}>
          <div className="grid gap-2 sm:grid-cols-2 lg:grid-cols-3">
            {choices.map((tag) => (
              <Checkbox
                key={tag}
                id={`settings-language-${tag}`}
                checked={form.languages.includes(tag)}
                disabled={disabled}
                onChange={(event) => update("languages", toggleLanguage(form.languages, tag, event.target.checked, choices))}
                label={labelOf(tag)}
              />
            ))}
          </div>
          {addable.length > 0 && isOwner ? (
            <Field label={t("settings.general.addLanguage")} className="max-w-sm">
              {(control) => (
                <Select
                  {...control}
                  value=""
                  disabled={disabled}
                  onChange={(event) => {
                    const tag = event.target.value;
                    if (tag) {
                      update("languages", toggleLanguage(form.languages, tag, true, choices));
                    }
                  }}
                >
                  <option value="">{t("settings.general.addLanguagePlaceholder")}</option>
                  {addable.map((item) => (
                    <option key={item.profile.tag} value={item.profile.tag}>
                      {capitalizeFirst(item.display_name, locale)}
                      {item.profile.native_name && item.profile.native_name !== item.display_name ? ` — ${item.profile.native_name}` : ""}
                    </option>
                  ))}
                </Select>
              )}
            </Field>
          ) : null}
        </Fieldset>

        <div className="grid gap-6 sm:grid-cols-2">
          <Field label={t("settings.general.defaultLanguage")} hint={t("settings.general.defaultLanguageHint")}>
            {(control) => (
              <Select
                {...control}
                value={form.languages.includes(form.defaultLanguage) ? form.defaultLanguage : (form.languages[0] ?? "")}
                disabled={disabled || form.languages.length === 0}
                onChange={(event) => update("defaultLanguage", event.target.value)}
              >
                {form.languages.map((tag) => (
                  <option key={tag} value={tag}>
                    {labelOf(tag)}
                  </option>
                ))}
              </Select>
            )}
          </Field>
          <Field label={t("settings.general.ownerLanguage")}>
            {(control) => (
              <Select {...control} value={form.ownerLanguage} disabled={disabled} onChange={(event) => update("ownerLanguage", event.target.value)}>
                {ownerLanguages.map((tag) => (
                  <option key={tag} value={tag}>
                    {labelOf(tag)}
                  </option>
                ))}
              </Select>
            )}
          </Field>
        </div>
      </div>
    </Card>
  );
}
