"use client";

import { useBusiness } from "@/components/business/BusinessContext";
import { Switch } from "@/components/content/Switch";
import { IconBell } from "@/components/icons";
import { Card, ErrorState, SkeletonText } from "@/components/ui";
import { useDigestPreferences, type DigestPreferencesBody } from "@/components/value/useValueQueries";
import type { DigestPreferences } from "@/components/value/valueModel";
import { useI18n } from "@/i18n/client";
import type { MessageKey } from "@/i18n/translate";

import { DigestChannelsSection, type DigestChannelChange } from "./DigestChannelsSection";

type Choice = "is_daily_digest_on" | "is_weekly_digest_on" | "is_monthly_report_on";

const CHOICES: readonly { field: Choice; label: MessageKey; hint: MessageKey }[] = [
  { field: "is_monthly_report_on", label: "reports.digests.monthly", hint: "reports.digests.monthlyHint" },
  { field: "is_weekly_digest_on", label: "reports.digests.weekly", hint: "reports.digests.weeklyHint" },
  { field: "is_daily_digest_on", label: "reports.digests.daily", hint: "reports.digests.dailyHint" },
];

/**
 * The signed-in owner's summaries (monthly report, weekly and daily
 * digests), each switched on or off at once, and where they arrive:
 * e-mail, devices, a Telegram chat or WhatsApp.
 */
export function DigestPreferencesCard() {
  const { t } = useI18n();
  const { business } = useBusiness();
  const { preferences, save } = useDigestPreferences(business.id);
  const stored = preferences.data;

  /** Saves a change shown at once (`shown`), back to what was stored if the API refuses it. */
  const saveChange = async (current: DigestPreferences, change: Partial<DigestPreferencesBody>, shown: Partial<DigestPreferences>) => {
    const body: DigestPreferencesBody = {
      is_daily_digest_on: current.is_daily_digest_on,
      is_weekly_digest_on: current.is_weekly_digest_on,
      is_monthly_report_on: current.is_monthly_report_on,
      ...change,
    };
    preferences.setData({ ...current, ...shown });
    const result = await save.run(body);
    preferences.setData(result.ok ? result.data : current);
    return result.ok;
  };

  const toggle = (current: DigestPreferences, field: Choice, isOn: boolean) => saveChange(current, { [field]: isOn }, { [field]: isOn });
  const changeChannels = (current: DigestPreferences, change: DigestChannelChange) =>
    saveChange(current, change, { channels: change.channels });

  return (
    <Card
      title={
        <span className="flex items-center gap-2">
          <IconBell className="size-4 text-accent" aria-hidden />
          {t("reports.digests.title")}
        </span>
      }
      description={t("reports.digests.description")}
    >
      {preferences.error && !stored ? (
        <ErrorState error={preferences.error} onRetry={preferences.reload} className="py-4" />
      ) : !stored ? (
        <SkeletonText lines={4} />
      ) : (
        <div className="space-y-4">
          <ul className="divide-y divide-line">
            {CHOICES.map((choice) => (
              <li key={choice.field} className="flex items-start justify-between gap-4 py-3 first:pt-0">
                <div className="min-w-0">
                  <p className="text-sm font-medium text-ink">{t(choice.label)}</p>
                  <p className="text-xs text-ink-muted">{t(choice.hint)}</p>
                </div>
                <Switch
                  label={t(choice.label)}
                  checked={stored[choice.field]}
                  disabled={save.isPending}
                  onChange={(isOn) => void toggle(stored, choice.field, isOn)}
                />
              </li>
            ))}
          </ul>
          <DigestChannelsSection
            preferences={stored}
            isSaving={save.isPending}
            onSave={(change) => changeChannels(stored, change)}
          />
        </div>
      )}
    </Card>
  );
}
