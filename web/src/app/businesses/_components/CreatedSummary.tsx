"use client";

import type { BusinessView, CountryProfileView } from "@/api/types";
import { IconCheck } from "@/components/icons";
import { Alert, Button, ButtonLink } from "@/components/ui";
import { useI18n } from "@/i18n/client";
import { countryName } from "@/lib/countries";
import { languageName } from "@/lib/format";
import { setupPath } from "@/lib/navigation";

import { languageOptions } from "../_lib/languageOptions";

/** After creation: what the business got from its country, and on to the profile. */
export function CreatedSummary({
  business,
  profile,
  onClose,
}: {
  business: BusinessView;
  profile: CountryProfileView | undefined;
  onClose: () => void;
}) {
  const { t, locale } = useI18n();
  const timezone = profile?.timezones.find((option) => option.name === business.timezone)?.display_name ?? business.timezone;
  const currency =
    profile && profile.profile.currency_code === business.currency_code
      ? `${profile.currency_display_name} (${business.currency_code})`
      : business.currency_code;
  const languageLabel = (tag: string) =>
    languageOptions(profile).find((option) => option.tag === tag)?.native_name ?? languageName(tag, locale);

  return (
    <div className="space-y-6">
      <Alert tone="success" title={t("businesses.createdTitle")}>
        {t("businesses.createdDescription", { country: countryName(business.country_code, locale) })}
      </Alert>
      <dl className="grid gap-4 text-sm sm:grid-cols-2">
        <div>
          <dt className="text-ink-subtle">{t("businesses.currency")}</dt>
          <dd className="mt-0.5 font-medium text-ink">{currency}</dd>
        </div>
        <div>
          <dt className="text-ink-subtle">{t("businesses.timezone")}</dt>
          <dd className="mt-0.5 font-medium text-ink">{timezone}</dd>
        </div>
        <div className="sm:col-span-2">
          <dt className="text-ink-subtle">{t("businesses.languages")}</dt>
          <dd className="mt-1 flex flex-wrap gap-2">
            {business.languages.map((tag) => (
              <span
                key={tag}
                lang={tag}
                className="inline-flex items-center gap-1 rounded-full border border-line bg-surface-muted px-2.5 py-1 text-xs font-medium text-ink"
              >
                {tag === business.default_language ? <IconCheck className="size-3.5 text-accent" aria-hidden /> : null}
                {languageLabel(tag)}
              </span>
            ))}
          </dd>
        </div>
      </dl>
      <div className="flex flex-col-reverse gap-3 sm:flex-row sm:justify-end">
        <Button variant="secondary" onClick={onClose}>
          {t("common.close")}
        </Button>
        <ButtonLink href={setupPath(business.id)}>{t("businesses.continueToProfile")}</ButtonLink>
      </div>
    </div>
  );
}
