"use client";

import { useBusiness } from "@/components/business/BusinessContext";
import { AutosaveHint } from "@/components/forms/AutosaveHint";
import { SavePill } from "@/components/forms/SavePill";
import { useAutosaveForm } from "@/components/forms/useAutosaveForm";
import { Card, SkeletonText } from "@/components/ui";
import { useI18n } from "@/i18n/client";
import { timeZoneLabel } from "@/lib/timeZones";

import {
  EVENT_LABELS,
  isSamePreferences,
  preferencesForm,
  preferencesFromForm,
  quietHoursErrors,
  type MyNotificationSettings,
  type NotificationPreferences,
  type PreferencesForm,
} from "../../_lib/notifications";
import type { useMyNotifications } from "../../_lib/useMyNotifications";
import { PreferencesFields } from "./PreferencesFields";

type MyNotifications = ReturnType<typeof useMyNotifications>;

/** "What reaches me": my events and quiet hours for my devices in this business. */
export function MyEventsCard({ mine }: { mine: MyNotifications }) {
  const { t, locale } = useI18n();
  const { business } = useBusiness();
  const stored = mine.settings.data;
  return (
    <Card
      aria-label={t("notifications.mine.title")}
      title={t("notifications.mine.title")}
      description={t("notifications.mine.description", { timeZone: timeZoneLabel(business.timezone, locale) })}
    >
      {stored ? <MyEventsForm key={stored.business_id} stored={stored} mine={mine} /> : <SkeletonText lines={4} />}
    </Card>
  );
}

/**
 * Saves itself: a checkbox at once, a time when it is complete; quiet
 * hours that are not valid yet wait (the error says why). Unticking an
 * event offers Undo for a few seconds.
 */
function MyEventsForm({ stored, mine }: { stored: MyNotificationSettings; mine: MyNotifications }) {
  const { t } = useI18n();
  const { savePreferences } = mine;
  const form = useAutosaveForm<PreferencesForm, MyNotificationSettings, NotificationPreferences>({
    stored,
    toForm: (settings) => preferencesForm(settings.preferences),
    invalidFields: (values) => Object.keys(quietHoursErrors(values)) as ("from" | "until")[],
    toBody: (values, base) => {
      const preferences = preferencesFromForm(values);
      return isSamePreferences(preferences, base.preferences) ? null : preferences;
    },
    save: (preferences) => savePreferences.run(preferences),
    onSaved: (saved) => mine.settings.setData(saved),
    undo: (before, after) => {
      const removed = before.events.find((event) => !after.events.includes(event));
      return removed ? t("notifications.mine.eventOff", { event: t(EVENT_LABELS[removed]) }) : null;
    },
  });

  return (
    <div className="space-y-5">
      <AutosaveHint state={form.state} />
      <PreferencesFields
        value={form.values}
        errors={quietHoursErrors(form.values)}
        status={(field) => <SavePill state={form.fieldState(field)} onRetry={form.retry} />}
        onChange={form.updateFields}
      />
    </div>
  );
}
