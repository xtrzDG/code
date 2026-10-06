"use client";

import { useState } from "react";

import { useBusinessFormat } from "@/components/business/BusinessContext";
import { IconCalendar } from "@/components/icons";
import { Badge, Button, Card, ConfirmDialog, useToast } from "@/components/ui";
import { useI18n } from "@/i18n/client";
import type { MessageKey } from "@/i18n/translate";

import { quotedMoneyText, type BillingOverview } from "../_lib/billing";
import { allowedPauseMonths, pauseCardState, pauseEndFor, type PauseUnavailableReason } from "../_lib/lifecycle";
import type { SubscriptionLifecycleActions } from "../_lib/useSubscriptionLifecycle";
import { PauseMonthsPicker } from "./PauseMonthsPicker";

const UNAVAILABLE: Record<Exclude<PauseUnavailableReason, "feature_off" | "already_paused">, MessageKey> = {
  not_active: "billingLifecycle.pause.unavailable.not_active",
  not_monthly: "billingLifecycle.pause.unavailable.not_monthly",
  allowance_used: "billingLifecycle.pause.unavailable.allowance_used",
};

const PAUSE_ERRORS = { conflict: "billingLifecycle.errors.pauseGone" } as const;

/**
 * Settings → Billing: the seasonal pause. Before a pause, how long and at
 * what price; once scheduled, its dates and "Call off"; while paused, until
 * when and "Resume full service" (asked first). Hidden until the platform
 * turns pausing on.
 */
export function PauseCard({
  overview,
  actions,
  canManage,
}: {
  overview: BillingOverview;
  actions: SubscriptionLifecycleActions;
  canManage: boolean;
}) {
  const { t } = useI18n();
  const format = useBusinessFormat();
  const toast = useToast();
  const [months, setMonths] = useState(1);
  const [isConfirmingResume, setConfirmingResume] = useState(false);
  const lifecycle = actions.lifecycle.data;
  const state = pauseCardState(overview, lifecycle);

  if (state.kind === "hidden") {
    return null;
  }

  const schedule = async (chosen: number) => {
    const result = await actions.pause.run(chosen);
    if (result.ok) {
      actions.applied(result.data, t("billingLifecycle.offers.taken.pause"));
    } else {
      toast.error(result.error, PAUSE_ERRORS);
    }
  };
  const resume = async (message: MessageKey) => {
    const result = await actions.resume.run();
    if (result.ok) {
      setConfirmingResume(false);
      actions.applied(result.data, t(message));
    } else {
      setConfirmingResume(false);
      toast.error(result.error, PAUSE_ERRORS);
    }
  };

  const percent = lifecycle?.pause.price_percent ?? 0;
  const title = (
    <span className="inline-flex items-center gap-2">
      <IconCalendar className="size-4 text-ink-subtle" aria-hidden />
      {t("billingLifecycle.pause.title")}
    </span>
  );

  if (state.kind === "paused" || state.kind === "scheduled") {
    const isPaused = state.kind === "paused";
    return (
      <Card
        title={title}
        actions={<Badge tone="info">{t(isPaused ? "billing.status.paused" : "billingLifecycle.pause.scheduledTitle")}</Badge>}
        footer={
          canManage ? (
            isPaused ? (
              <Button size="sm" onClick={() => setConfirmingResume(true)} disabled={actions.isPending}>
                {t("billingLifecycle.pause.resume")}
              </Button>
            ) : (
              <Button
                size="sm"
                variant="secondary"
                onClick={() => void resume("billingLifecycle.pause.calledOff")}
                isLoading={actions.resume.isPending}
                disabled={actions.isPending}
              >
                {t("billingLifecycle.pause.callOff")}
              </Button>
            )
          ) : undefined
        }
      >
        <div className="space-y-1.5 text-sm">
          <p className="font-medium text-ink">
            {isPaused
              ? t("billingLifecycle.pause.pausedTitle", { date: format.date(state.until) })
              : t("billingLifecycle.pause.window", { start: format.date(state.startsAt), until: format.date(state.until) })}
          </p>
          <p className="text-ink-muted">
            {isPaused
              ? t("billingLifecycle.pause.paused", { percent })
              : t("billingLifecycle.pause.scheduled", {
                  start: format.date(state.startsAt),
                  until: format.date(state.until),
                })}
          </p>
        </div>
        <ConfirmDialog
          open={isConfirmingResume}
          onClose={() => setConfirmingResume(false)}
          onConfirm={() => resume("billingLifecycle.pause.resumed")}
          tone="primary"
          isPending={actions.resume.isPending}
          title={t("billingLifecycle.pause.resumeTitle")}
          description={t("billingLifecycle.pause.resumeDescription")}
          confirmLabel={t("billingLifecycle.pause.resume")}
        />
      </Card>
    );
  }

  if (state.kind === "unavailable") {
    return (
      <Card title={title} description={t("billingLifecycle.pause.description")}>
        <p className="text-sm text-ink-muted">{t(UNAVAILABLE[state.reason])}</p>
      </Card>
    );
  }

  const options = state.options;
  const chosen = allowedPauseMonths(months, options.max_months);
  const startsAt = options.starts_at ?? null;
  const endsAt = pauseEndFor(options, chosen);
  return (
    <Card
      title={title}
      description={t("billingLifecycle.pause.description")}
      footer={
        canManage && startsAt ? (
          <Button
            size="sm"
            onClick={() => void schedule(chosen)}
            isLoading={actions.pause.isPending}
            disabled={actions.isPending}
          >
            {t("billingLifecycle.pause.submit", { date: format.date(startsAt) })}
          </Button>
        ) : undefined
      }
    >
      <div className="space-y-4 text-sm">
        {options.monthly_price ? (
          <p className="font-medium text-ink">
            {t("billingLifecycle.pause.price", {
              price: quotedMoneyText(options.monthly_price, format.money),
              percent: options.price_percent,
            })}
          </p>
        ) : null}
        <PauseMonthsPicker maxMonths={options.max_months} value={chosen} onChange={setMonths} disabled={!canManage || actions.isPending} />
        {startsAt && endsAt ? (
          <p className="text-ink-muted" aria-live="polite">
            {t("billingLifecycle.pause.window", { start: format.date(startsAt), until: format.date(endsAt) })}
          </p>
        ) : null}
        {options.paused_months > 0 ? (
          <p className="text-ink-subtle">
            {t("billingLifecycle.pause.allowance", {
              used: options.paused_months,
              cap: options.cap_months,
              window: options.window_months,
            })}
          </p>
        ) : null}
      </div>
    </Card>
  );
}
