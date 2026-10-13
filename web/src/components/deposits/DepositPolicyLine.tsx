"use client";

import { useBusinessFormat } from "@/components/business/BusinessContext";
import { useI18n } from "@/i18n/client";

import { policySummary, type DepositPolicyView } from "./depositModel";

/** "Deposit GEL 20.00 per guest · from 6 guests": a policy in one line, under a resource's or service's name. */
export function DepositPolicyLine({ policy }: { policy: DepositPolicyView }) {
  const { t, tp } = useI18n();
  const format = useBusinessFormat();
  const summary = policySummary(policy);
  const text = t(summary.key, {
    amount: summary.amountMinor === null ? "" : format.money(summary.amountMinor, policy.currency_code),
    percent: summary.percent ?? "",
  });
  return (
    <p className="text-sm text-ink-muted">
      {summary.fromGuests === null ? text : `${text} · ${tp("deposits.policy.fromGuests", summary.fromGuests)}`}
    </p>
  );
}
