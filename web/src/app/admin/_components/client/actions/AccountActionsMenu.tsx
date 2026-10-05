"use client";

import { useState } from "react";

import type { Schema } from "@/api/types";
import { OverflowMenu } from "@/components/ui";
import { useI18n } from "@/i18n/client";

import { availableActions, type AccountAction } from "../../../_lib/accountActions";
import { CreditDialog, DiscountDialog } from "./DiscountAndCreditDialogs";
import { ManualPaymentDialog, OverridePlanDialog } from "./PaymentAndPlanDialogs";
import { ExtendTrialDialog, WaiveSetupFeeDialog } from "./TrialAndFeeDialogs";

const ACTION_LABELS = {
  extend: "adminActions.extend.action",
  discount: "adminActions.discount.action",
  credit: "adminActions.credit.action",
  waive: "adminActions.waive.action",
  payment: "adminActions.payment.action",
  plan: "adminActions.plan.action",
} as const satisfies Record<AccountAction, string>;

/**
 * "Account actions" on the admin client page: a longer trial, a discount,
 * credit, the setup fee waived, a payment recorded by hand, a plan set by
 * hand. Shown to admins whose role manages client billing; each action asks
 * why, and the client's audit log keeps the answer. Every opening is a
 * fresh dialog (its key changes), so no half-typed values come back.
 */
export function AccountActionsMenu({ businessId, client }: { businessId: string; client: Schema<"ClientHealthView"> }) {
  const { t } = useI18n();
  const [active, setActive] = useState<AccountAction | null>(null);
  const [opening, setOpening] = useState(0);
  const { summary, account } = client;
  const actions = availableActions(account, client.invoices ?? [], Boolean(summary.subscription_status));
  if (actions.length === 0) {
    return null;
  }

  const open = (action: AccountAction) => {
    setOpening((count) => count + 1);
    setActive(action);
  };
  const close = () => setActive(null);
  const common = { businessId, name: summary.name, onClose: close };
  const autoDebitNote = summary.has_auto_debit ? t("adminActions.autoDebitNote") : undefined;
  const currency = account?.credit_balance?.currency_code ?? summary.currency_code;

  return (
    <>
      <OverflowMenu
        label={t("adminActions.menu")}
        placement="bottom"
        actions={actions.map((action) => ({ key: action, label: t(ACTION_LABELS[action]), onSelect: () => open(action) }))}
      />
      {actions.includes("extend") ? <ExtendTrialDialog key={`extend-${opening}`} {...common} open={active === "extend"} /> : null}
      {actions.includes("discount") ? (
        <DiscountDialog
          key={`discount-${opening}`}
          {...common}
          open={active === "discount"}
          timeZone={client.timezone}
          autoDebitNote={autoDebitNote}
        />
      ) : null}
      {actions.includes("credit") ? (
        <CreditDialog key={`credit-${opening}`} {...common} open={active === "credit"} currency={currency} autoDebitNote={autoDebitNote} />
      ) : null}
      {actions.includes("waive") ? <WaiveSetupFeeDialog key={`waive-${opening}`} {...common} open={active === "waive"} /> : null}
      {actions.includes("payment") ? (
        <ManualPaymentDialog
          key={`payment-${opening}`}
          {...common}
          open={active === "payment"}
          invoices={client.invoices ?? []}
          timeZone={client.timezone}
        />
      ) : null}
      {actions.includes("plan") ? (
        <OverridePlanDialog
          key={`plan-${opening}`}
          {...common}
          open={active === "plan"}
          currentPlan={summary.plan_key}
          currentPeriod={summary.billing_period}
        />
      ) : null}
    </>
  );
}
