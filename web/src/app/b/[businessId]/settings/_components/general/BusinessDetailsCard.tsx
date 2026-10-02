"use client";

import Link from "next/link";

import { Card, Field, Input } from "@/components/ui";
import { Facts } from "@/components/workspace/Facts";
import { useI18n } from "@/i18n/client";
import type { MessageKey } from "@/i18n/translate";
import { countryFlag, countryName } from "@/lib/countries";
import { businessPath } from "@/lib/navigation";

import { MAX_BUSINESS_NAME_LENGTH, MAX_CITY_LENGTH, type BusinessView } from "../../_lib/general";
import type { GeneralSettings } from "../../_lib/useGeneralSettings";

const PLAN_NAMES: Record<BusinessView["plan_key"], MessageKey> = {
  chat: "workspace.plans.chat",
  voice_and_chat: "workspace.plans.voice_and_chat",
  plus: "workspace.plans.plus",
};

/** The business's name and city, and what cannot be changed here (country, currency, data region, plan). */
export function BusinessDetailsCard({ settings }: { settings: GeneralSettings }) {
  const { t, locale } = useI18n();
  const { form, baseline, disabled, update, errorText } = settings;
  return (
    <Card title={t("settings.general.businessTitle")}>
      <div className="space-y-6">
        <div className="grid gap-6 sm:grid-cols-2">
          <Field label={t("settings.general.name")} required error={errorText("name")}>
            {(control) => (
              <Input
                {...control}
                value={form.name}
                maxLength={MAX_BUSINESS_NAME_LENGTH}
                dir="auto"
                autoComplete="organization"
                disabled={disabled}
                onChange={(event) => update("name", event.target.value)}
              />
            )}
          </Field>
          <Field label={t("settings.general.city")} optionalLabel={t("common.optional")} error={errorText("city")}>
            {(control) => (
              <Input
                {...control}
                value={form.city}
                maxLength={MAX_CITY_LENGTH}
                dir="auto"
                autoComplete="address-level2"
                disabled={disabled}
                onChange={(event) => update("city", event.target.value)}
              />
            )}
          </Field>
        </div>
        <Facts
          columns={4}
          items={[
            {
              label: t("settings.general.country"),
              value: `${countryFlag(baseline.country_code)} ${countryName(baseline.country_code, locale)}`,
            },
            { label: t("settings.general.currency"), value: baseline.currency_code },
            {
              label: t("settings.general.dataRegion"),
              value: t(baseline.data_region === "us" ? "settings.general.dataRegions.us" : "settings.general.dataRegions.eu"),
            },
            {
              label: t("settings.general.plan"),
              value: (
                <Link href={businessPath(baseline.id, "settings/billing")} className="text-accent hover:underline" title={t("settings.general.planHint")}>
                  {t(PLAN_NAMES[baseline.plan_key])}
                </Link>
              ),
            },
          ]}
        />
      </div>
    </Card>
  );
}
