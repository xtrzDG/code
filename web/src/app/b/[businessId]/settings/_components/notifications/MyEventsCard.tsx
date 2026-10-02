"use client";

import { useState } from "react";

import { useBusiness } from "@/components/business/BusinessContext";
import { Button, Card, InlineError, SkeletonText, useToast } from "@/components/ui";
import { useI18n } from "@/i18n/client";

import {
  isSamePreferences,
  preferencesForm,
  preferencesFromForm,
  quietHoursErrors,
  type MyNotificationSettings,
  type PreferencesForm,
} from "../../_lib/notifications";
import type { useMyNotifications } from "../../_lib/useMyNotifications";
import { PreferencesFields } from "./PreferencesFields";

type MyNotifications = ReturnType<typeof useMyNotifications>;

/** "What reaches me": my events and quiet hours for my devices in this business. */
export function MyEventsCard({ mine }: { mine: MyNotifications }) {
  const { t } = useI18n();
  const { business } = useBusiness();
  const stored = mine.settings.data;
  return (
    <Card
      aria-label={t("notifications.mine.title")}
      title={t("notifications.mine.title")}
      description={t("notifications.mine.description", { timeZone: business.timezone })}
    >
      {stored ? <MyEventsForm key={stored.business_id} stored={stored} mine={mine} /> : <SkeletonText lines={4} />}
    </Card>
  );
}

function MyEventsForm({ stored, mine }: { stored: MyNotificationSettings; mine: MyNotifications }) {
  const { t } = useI18n();
  const toast = useToast();
  const [form, setForm] = useState<PreferencesForm>(() => preferencesForm(stored.preferences));
  const [isChecked, setIsChecked] = useState(false);
  const errors = isChecked ? quietHoursErrors(form) : {};
  const isChanged = !isSamePreferences(preferencesFromForm(form), stored.preferences);
  const { savePreferences } = mine;

  const save = async () => {
    setIsChecked(true);
    if (Object.keys(quietHoursErrors(form)).length > 0) {
      return;
    }
    const result = await savePreferences.run(preferencesFromForm(form));
    if (result.ok) {
      mine.settings.setData(result.data);
      setForm(preferencesForm(result.data.preferences));
      setIsChecked(false);
      toast.success(t("notifications.mine.saved"));
    }
  };

  return (
    <form
      noValidate
      className="space-y-5"
      onSubmit={(event) => {
        event.preventDefault();
        void save();
      }}
    >
      <PreferencesFields value={form} errors={errors} disabled={savePreferences.isPending} onChange={setForm} />
      <InlineError error={savePreferences.error} />
      <div className="flex items-center justify-end gap-3">
        <Button type="submit" disabled={!isChanged} isLoading={savePreferences.isPending} loadingText={t("common.saving")}>
          {t("notifications.mine.save")}
        </Button>
      </div>
    </form>
  );
}
