"use client";

import Link from "next/link";

import { useBusiness } from "@/components/business/BusinessContext";
import { Switch } from "@/components/content/Switch";
import { IconBell } from "@/components/icons";
import { Card, ErrorState, SkeletonText } from "@/components/ui";
import { useDigestPreferences } from "@/components/value/useValueQueries";
import type { DigestPreferences } from "@/components/value/valueModel";
import { useI18n } from "@/i18n/client";
import type { MessageKey } from "@/i18n/translate";
import { businessPath } from "@/lib/navigation";

type Choice = "is_daily_digest_on" | "is_weekly_digest_on" | "is_monthly_report_on";

const CHOICES: readonly { field: Choice; label: MessageKey; hint: MessageKey }[] = [
  { field: "is_monthly_report_on", label: "reports.digests.monthly", hint: "reports.digests.monthlyHint" },
  { field: "is_weekly_digest_on", label: "reports.digests.weekly", hint: "reports.digests.weeklyHint" },
  { field: "is_daily_digest_on", label: "reports.digests.daily", hint: "reports.digests.dailyHint" },
];

/**
 * The signed-in owner's summaries (monthly report, weekly and daily
 * digests), each switched on or off at once, and where they arrive: the
 * sign-in e-mail and the devices with notifications on.
 */
export function DigestPreferencesCard() {
  const { t, tp } = useI18n();
  const { business } = useBusiness();
  const { preferences, save } = useDigestPreferences(business.id);
  const stored = preferences.data;

  const toggle = async (current: DigestPreferences, field: Choice, isOn: boolean) => {
    const body = {
      is_daily_digest_on: current.is_daily_digest_on,
      is_weekly_digest_on: current.is_weekly_digest_on,
      is_monthly_report_on: current.is_monthly_report_on,
      [field]: isOn,
    };
    preferences.setData({ ...current, [field]: isOn });
    const result = await save.run(body);
    preferences.setData(result.ok ? result.data : current);
  };

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
          <div className="space-y-1.5 rounded-xl bg-surface-muted/60 p-3 text-xs text-ink-muted">
            <p>
              {stored.email
                ? stored.is_email_ready
                  ? t("reports.digests.email", { email: stored.email })
                  : t("reports.digests.emailNotReady")
                : t("reports.digests.noEmail")}
            </p>
            <p>{stored.device_count > 0 ? tp("reports.digests.devices", stored.device_count) : t("reports.digests.noDevices")}</p>
            <Link href={businessPath(business.id, "settings/notifications")} className="inline-block font-medium text-accent hover:underline">
              {t("reports.digests.manageDevices")}
            </Link>
          </div>
        </div>
      )}
    </Card>
  );
}
