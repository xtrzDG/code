"use client";

import { useBusiness } from "@/components/business/BusinessContext";
import { Field, Select } from "@/components/ui";
import { useI18n } from "@/i18n/client";
import { languageName } from "@/lib/format";

/** The language of the text prepared for the customer (one of the business languages). */
export function CustomerLanguageSelect({ value, onChange }: { value: string; onChange: (language: string) => void }) {
  const { t, locale } = useI18n();
  const { business } = useBusiness();
  return (
    <Field label={t("bookings.form.language")} hint={t("bookings.form.languageHint")}>
      {(control) => (
        <Select {...control} value={value} onChange={(event) => onChange(event.target.value)}>
          {business.languages.map((language) => (
            <option key={language} value={language}>
              {languageName(language, locale)}
            </option>
          ))}
        </Select>
      )}
    </Field>
  );
}
