"use client";

import type { ReactNode } from "react";

import { Checkbox, Field, Fieldset, TimeField } from "@/components/ui";
import { useI18n } from "@/i18n/client";

import {
  ALL_EVENTS,
  EVENT_LABELS,
  toggleEvent,
  type PreferencesForm,
  type QuietHoursError,
} from "../../_lib/notifications";

const QUIET_ERRORS = {
  format: "notifications.preferences.errors.format",
  same: "notifications.preferences.errors.same",
} as const satisfies Record<QuietHoursError, string>;

/**
 * Which events reach someone, and their quiet hours (a staff contact's, or
 * my own). `status` puts a field's "Saved" beside it in a form that saves
 * itself.
 */
export function PreferencesFields({
  value,
  errors,
  disabled = false,
  status,
  onChange,
}: {
  value: PreferencesForm;
  errors: { from?: QuietHoursError; until?: QuietHoursError };
  disabled?: boolean;
  status?: (field: keyof PreferencesForm) => ReactNode;
  onChange: (next: PreferencesForm) => void;
}) {
  const { t } = useI18n();
  return (
    <div className="space-y-5">
      <Fieldset
        legend={t("notifications.preferences.events")}
        error={value.events.length === 0 ? t("notifications.preferences.noEvents") : undefined}
        status={status?.("events")}
      >
        <div className="grid grid-cols-[repeat(auto-fit,minmax(13rem,1fr))] gap-2.5">
          {ALL_EVENTS.map((event) => (
            <Checkbox
              key={event}
              className="rounded-xl border border-line bg-surface px-3 py-2.5 transition-colors has-checked:border-accent/40 has-checked:bg-accent-soft"
              label={t(EVENT_LABELS[event])}
              checked={value.events.includes(event)}
              disabled={disabled}
              onChange={(change) => onChange({ ...value, events: toggleEvent(value.events, event, change.target.checked) })}
            />
          ))}
        </div>
      </Fieldset>
      <Fieldset
        legend={t("notifications.preferences.quietHours")}
        hint={t("notifications.preferences.quietHoursHint")}
        status={status?.("hasQuietHours")}
      >
        <Checkbox
          label={t("notifications.preferences.quietHoursToggle")}
          checked={value.hasQuietHours}
          disabled={disabled}
          onChange={(change) => onChange({ ...value, hasQuietHours: change.target.checked })}
        />
        {value.hasQuietHours ? (
          <div className="grid max-w-sm grid-cols-2 gap-3">
            <Field
              label={t("notifications.preferences.quietFrom")}
              error={errors.from ? t(QUIET_ERRORS[errors.from]) : undefined}
              status={status?.("from")}
            >
              {(control) => (
                <TimeField
                  {...control}
                  value={value.from}
                  step={30}
                  disabled={disabled}
                  onChange={(from) => onChange({ ...value, from })}
                />
              )}
            </Field>
            <Field
              label={t("notifications.preferences.quietUntil")}
              error={errors.until ? t(QUIET_ERRORS[errors.until]) : undefined}
              status={status?.("until")}
            >
              {(control) => (
                <TimeField
                  {...control}
                  value={value.until}
                  step={30}
                  disabled={disabled}
                  onChange={(until) => onChange({ ...value, until })}
                />
              )}
            </Field>
          </div>
        ) : null}
      </Fieldset>
    </div>
  );
}
