"use client";

import { api } from "@/api/client";
import { queryKeys } from "@/api/queryKeys";
import { useMutation } from "@/api/useMutation";
import { useQuery } from "@/api/useQuery";
import { useBusiness } from "@/components/business/BusinessContext";
import { Switch } from "@/components/content/Switch";
import { Card, ErrorState, SkeletonText } from "@/components/ui";
import { useI18n } from "@/i18n/client";

/**
 * The owner's setup reminders (GET/PUT …/setup/reminders): a few short
 * messages in the first days, in Telegram, by e-mail and on the devices, when the
 * assistant is not live yet or has no second channel or first customer.
 * One switch for the whole business; owners only.
 */
export function SetupRemindersCard() {
  const { t } = useI18n();
  const { business } = useBusiness();
  const path = { params: { path: { business_id: business.id } } };
  const reminders = useQuery(queryKeys.setup.reminders(business.id), () =>
    api.GET("/v1/businesses/{business_id}/setup/reminders", path),
  );
  const save = useMutation((isOn: boolean) =>
    api.PUT("/v1/businesses/{business_id}/setup/reminders", { ...path, body: { is_on: isOn } }),
  );
  const stored = reminders.data;

  const toggle = async (isOn: boolean) => {
    if (!stored) {
      return;
    }
    reminders.setData({ ...stored, is_on: isOn });
    const result = await save.run(isOn);
    reminders.setData(result.ok ? result.data : stored);
  };

  return (
    <Card title={t("notifications.setupReminders.title")}>
      {reminders.error && !stored ? (
        <ErrorState error={reminders.error} onRetry={reminders.reload} className="py-4" />
      ) : !stored ? (
        <SkeletonText lines={2} />
      ) : (
        <div className="flex items-start justify-between gap-4">
          <p id="setup-reminders-hint" className="min-w-0 text-sm text-ink-muted">
            {t("notifications.setupReminders.description")}
          </p>
          <Switch
            label={t("notifications.setupReminders.label")}
            describedBy="setup-reminders-hint"
            checked={stored.is_on}
            disabled={save.isPending}
            onChange={(isOn) => void toggle(isOn)}
          />
        </div>
      )}
    </Card>
  );
}
