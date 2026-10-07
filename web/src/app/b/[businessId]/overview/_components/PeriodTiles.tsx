"use client";

import type { Schema } from "@/api/types";
import { useBusiness, useBusinessFormat } from "@/components/business/BusinessContext";
import { formatPercent } from "@/components/insights/numbers";
import { AnimatedNumber } from "@/components/motion";
import { DeltaChip } from "@/components/value/DeltaChip";
import { FirstPeriodNote } from "@/components/value/FirstPeriodNote";
import {
  bookedValueIn,
  formatWholeMoney,
  hadNoActivity,
  periodDays,
  type Polarity,
  type ValueModel,
  type ValueTotalsNumber,
} from "@/components/value/valueModel";
import { useI18n } from "@/i18n/client";

import { StatTile } from "./DashboardWidgets";

type DashboardStats = Schema<"DashboardStats">;

/**
 * The period's six headline numbers, each with how it moved since the
 * period before (from the value model of the same dates; no chips until
 * it arrives or while it is for other dates; after a period without any
 * activity, one note instead of a chip on every number), and for owners
 * what all the period's bookings are worth at their own prices (services,
 * stays), those added by hand included.
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
  const { t, tp, locale } = useI18n();
  const format = useBusinessFormat();
  const { business, isOwner } = useBusiness();
  const booked = isOwner ? bookedValueIn(data.booked_value ?? [], business.currency_code) : null;
  const money = (minor: number, currency: string) => formatWholeMoney(minor, currency, locale);
  const compared = value && value.date_from === data.date_from && value.date_to === data.date_to ? value : null;
  const days = periodDays(data.date_from, data.date_to);
  const isFirstPeriod = compared ? hadNoActivity(compared.previous) : false;

  const chip = (field: Exclude<ValueTotalsNumber, "estimated_revenue_minor">, polarity: Polarity = "more-is-better") =>
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
    <div className="space-y-2">
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
          hint={tp("dashboard.kpi.afterHoursHint", data.conversation_count, {
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
        {booked ? (
          <StatTile
            className="col-span-2 sm:col-span-3"
            label={t("dashboard.kpi.bookedValue")}
            value={
              booked.main ? (
                <AnimatedNumber value={booked.main.value_minor} format={(minor) => money(minor, business.currency_code)} />
              ) : (
                booked.others.map((total) => money(total.value_minor, total.currency_code)).join(" · ")
              )
            }
            hint={[
              [
                booked.main
                  ? tp("dashboard.kpi.bookedValueHint", booked.main.booking_count, { count: format.number(booked.main.booking_count) })
                  : null,
                booked.main && booked.others.length > 0
                  ? t("dashboard.kpi.bookedValueOther", {
                      money: booked.others.map((total) => money(total.value_minor, total.currency_code)).join(", "),
                    })
                  : null,
              ]
                .filter(Boolean)
                .join(" "),
              // Unlike the hero (the assistant's bookings), every booking counts here.
              t("dashboard.kpi.bookedValueScope"),
            ]
              .filter(Boolean)
              .join(" · ")}
          />
        ) : null}
      </dl>
      {compared && isFirstPeriod ? <FirstPeriodNote /> : null}
    </div>
  );
}
