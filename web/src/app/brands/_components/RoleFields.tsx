"use client";

import { Checkbox, Fieldset, Radio } from "@/components/ui";
import { useI18n } from "@/i18n/client";
import { cn } from "@/lib/cn";

import { BRAND_ROLES, type BrandLocationView, type BrandMemberRole } from "../_lib/brands";

/**
 * A member's role in the brand and, for a regional manager, the locations
 * they work in: the only ones they will see.
 */
export function RoleFields({
  idPrefix,
  role,
  businessIds,
  locations,
  locationsError,
  onChange,
}: {
  idPrefix: string;
  role: BrandMemberRole;
  businessIds: readonly string[];
  locations: readonly BrandLocationView[];
  locationsError?: string;
  onChange: (change: { role?: BrandMemberRole; businessIds?: string[] }) => void;
}) {
  const { t } = useI18n();
  const toggle = (businessId: string, isOn: boolean) =>
    onChange({ businessIds: isOn ? [...businessIds, businessId] : businessIds.filter((id) => id !== businessId) });

  return (
    <>
      <fieldset className="space-y-2">
        <legend className="text-sm font-medium text-ink">{t("brands.team.role")}</legend>
        <div className="space-y-2">
          {BRAND_ROLES.map((option) => (
            <Radio
              key={option}
              id={`${idPrefix}-role-${option}`}
              name={`${idPrefix}-role`}
              checked={role === option}
              onChange={() => onChange({ role: option })}
              className={cn(
                "rounded-xl border p-3 transition-colors",
                role === option ? "border-accent-solid bg-accent-soft/40" : "border-line hover:bg-surface-muted/60",
              )}
              label={<span className="font-medium">{t(`brands.roles.${option}`)}</span>}
              description={t(`brands.roleDescriptions.${option}`)}
            />
          ))}
        </div>
      </fieldset>
      {role === "regional_manager" ? (
        <Fieldset legend={t("brands.team.locations")} error={locationsError}>
          <div className="space-y-2">
            {locations.map((location) => (
              <Checkbox
                key={location.business_id}
                id={`${idPrefix}-location-${location.business_id}`}
                checked={businessIds.includes(location.business_id)}
                onChange={(event) => toggle(location.business_id, event.target.checked)}
                label={<span data-user-content>{[location.name, location.city].filter(Boolean).join(" · ")}</span>}
              />
            ))}
          </div>
        </Fieldset>
      ) : null}
    </>
  );
}
