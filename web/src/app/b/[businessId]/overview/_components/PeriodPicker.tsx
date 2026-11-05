"use client";

/**
 * The Overview's period choice. The chosen period shows at once, while the
 * dashboard redraws for it in a transition (useOptimisticChoice).
 */

import { SegmentedControl } from "@/components/insights/SegmentedControl";
import { useI18n } from "@/i18n/client";
import { useOptimisticChoice } from "@/lib/useOptimisticChoice";

import { DASHBOARD_PERIODS, type DashboardPeriod } from "./dashboardModel";

export function PeriodPicker({ value, onChange }: { value: DashboardPeriod; onChange: (period: DashboardPeriod) => void }) {
  const { t } = useI18n();
  const [shown, choose] = useOptimisticChoice(value, onChange);
  return (
    <SegmentedControl
      label={t("dashboard.periodLabel")}
      value={shown}
      onChange={choose}
      options={DASHBOARD_PERIODS.map((period) => ({ value: period, label: t(`dashboard.periods.${period}`) }))}
    />
  );
}
