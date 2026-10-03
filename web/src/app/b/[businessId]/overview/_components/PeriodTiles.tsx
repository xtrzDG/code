"use client";

import type { Schema } from "@/api/types";
import { useBusinessFormat } from "@/components/business/BusinessContext";
import { formatPercent } from "@/components/insights/numbers";
import { AnimatedNumber } from "@/components/motion";
import { DeltaChip } from "@/components/value/DeltaChip";
import { hadNoActivity, periodDays, type Polarity, type ValueModel, type ValueTotals } from "@/components/value/valueModel";
import { useI18n } from "@/i18n/client";

import { StatTile } from "./DashboardWidgets";

type DashboardStats = Schema<"DashboardStats">;

/**
 * The period's six headline numbers, each with how it moved since the
 * period before (from the value model of the same dates; no chips until
 * it arrives or while it is for other dates).
 */
export function PeriodTiles({
  data,
  value,
  isBusy,
}: {
  data: DashboardStats;
  value: ValueModel | undefined;
  isBusy: boolean;
}) {
  const { t, locale } = useI18n();
  const format = useBusinessFormat();
  const compared = value && value.date_from === data.date_from && value.date_to === data.date_to ? value : null;
  const days = periodDays(data.date_from, data.date_to);
  const isFirstPeriod = compared ? hadNoActivity(compared.previous) : false;

  const chip = (field: keyof Omit<ValueTotals, "estimated_revenue_minor">, polarity: Polarity = "more-is-better") =>
    compared ? (
      <DeltaChip
        current={compared.current[field]}
        previous={compared.previous[field]}
        days={days}
        polarity={polarity}
        isFirstPeriod={isFirstPeriod}
      />
    ) : null;

  return (
    <dl className="grid grid-cols-2 gap-3 sm:grid-cols-3" aria-busy={isBusy || undefined}>
      <StatTile
        label={t("dashboard.kpi.conversations")}
        value={<AnimatedNumber value={data.conversation_count} format={format.number} />}
        hint={t("dashboard.kpi.conversationsHint")}
        chip={chip("conversation_count")}
      />
      <StatTile
        label={t("dashboard.kpi.messages")}
        value={<AnimatedNumber value={data.customer_message_count} format={format.number} />}
        chip={chip("customer_message_count")}
      />
      <StatTile
        label={t("dashboard.kpi.bookings")}
        value={<AnimatedNumber value={data.booking_count} format={format.number} />}
        chip={chip("booking_count")}
      />
      <StatTile
        label={t("dashboard.kpi.afterHours")}
        value={<AnimatedNumber value={data.after_hours_share_percent} format={(percent) => formatPercent(percent, locale)} />}
        hint={t("dashboard.kpi.afterHoursHint", {
          count: format.number(data.after_hours_conversation_count),
          total: format.number(data.conversation_count),
        })}
        chip={chip("after_hours_conversation_count")}
      />
      <StatTile
        label={t("dashboard.kpi.leads")}
        value={<AnimatedNumber value={data.lead_count} format={format.number} />}
        chip={chip("request_count")}
      />
      <StatTile
        label={t("dashboard.kpi.handoffs")}
        value={<AnimatedNumber value={data.handoff_count} format={format.number} />}
        chip={chip("handoff_count", "neutral")}
      />
    </dl>
  );
}
