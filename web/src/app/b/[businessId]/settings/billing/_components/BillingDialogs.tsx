"use client";

import { useBusinessFormat } from "@/components/business/BusinessContext";
import { ConfirmDialog } from "@/components/ui";
import { useI18n } from "@/i18n/client";

import { planPrice, quotedMoneyText, type BillingOverview, type BillingPeriod } from "../_lib/billing";
import type { BillingActions } from "../_lib/useBillingActions";
import type { SubscriptionLifecycleActions } from "../_lib/useSubscriptionLifecycle";
import { CancelSubscriptionDialog } from "./CancelSubscriptionDialog";
import type { PlanChoice } from "./PlansSection";
import { SetupOptionPicker } from "./SetupOptionPicker";

/** Confirming a plan choice (a trial, a subscription or a switch), and the cancel dialog with its offers. */
export function BillingDialogs({
  actions,
  lifecycle,
  data,
}: {
  actions: BillingActions;
  lifecycle: SubscriptionLifecycleActions;
  data: BillingOverview | undefined;
}) {
  const { t, locale } = useI18n();
  const format = useBusinessFormat();
  const { choice, dialogError } = actions;

  const periodName = (period: BillingPeriod) =>
    t(period === "annual" ? "billing.periodNames.annual" : "billing.periodNames.monthly").toLocaleLowerCase(locale);
  const pricePer = (choice: PlanChoice) =>
    t(choice.period === "annual" ? "billing.pricePer.annual" : "billing.pricePer.monthly", {
      price: quotedMoneyText(planPrice(choice.quote, choice.period), format.money),
    });

  const choiceTitle = (choice: PlanChoice): string => {
    switch (choice.action) {
      case "trial":
        return t("billing.dialogs.trialTitle", { plan: choice.quote.name });
      case "subscribe":
        return t("billing.subscribe.title", { plan: choice.quote.name, period: periodName(choice.period) });
      case "switch":
        return t("billing.dialogs.changeTitle", { plan: choice.quote.name, period: periodName(choice.period) });
    }
  };

  const choiceDescription = (choice: PlanChoice): string => {
    switch (choice.action) {
      case "trial":
        return t("billing.dialogs.trialDescription", { days: choice.quote.trial_days, price: pricePer(choice) });
      case "subscribe": {
        const price = quotedMoneyText(planPrice(choice.quote, choice.period), format.money);
        return choice.period === "annual"
          ? t("billing.subscribe.descriptionAnnual", { price })
          : t("billing.subscribe.description", { price });
      }
      case "switch":
        return t("billing.dialogs.changeDescription", { price: pricePer(choice) });
    }
  };

  return (
    <>
      <ConfirmDialog
        open={choice !== null}
        onClose={actions.closeChoice}
        onConfirm={actions.onConfirmChoice}
        tone="primary"
        isPending={actions.isChoosing}
        error={dialogError}
        errorOverrides={
          choice?.action === "subscribe"
            ? { conflict: "billing.errors.nothingToPay" }
            : { conflict: "billing.errors.trialUsed", not_found: "billing.errors.noSubscription" }
        }
        title={choice ? choiceTitle(choice) : ""}
        confirmLabel={
          choice?.action === "trial"
            ? t("billing.dialogs.trialConfirm")
            : choice?.action === "subscribe"
              ? t("billing.subscribe.confirm")
              : t("billing.dialogs.changeConfirm")
        }
      >
        {choice ? <p>{choiceDescription(choice)}</p> : null}
        {choice?.action === "subscribe" ? (
          <SetupOptionPicker
            quote={choice.quote}
            period={choice.period}
            value={actions.setupOption}
            onChange={actions.setSetupOption}
            disabled={actions.isChoosing}
          />
        ) : null}
      </ConfirmDialog>

      <CancelSubscriptionDialog
        open={actions.isCancelling}
        onClose={actions.closeCancel}
        overview={data}
        actions={lifecycle}
      />
    </>
  );
}
