/**
 * Deposits in the cabinet, as pure functions: the policy of a table, room,
 * master, service or the banquet requests as a form (amounts typed in the
 * business currency's major units, sent in minor units), its one-line
 * summary, the labels and tones of a deposit's status, and the booking as
 * it reads once its deposit is marked paid.
 */

import type { BadgeTone } from "@/components/ui";
import type { BookingView } from "@/components/insights/types";
import type { MessageKey } from "@/i18n/translate";
import type { RequestBody, Schema } from "@/api/types";
import {
  currencyFractionDigits,
  decimalInputValue,
  majorToMinor,
  minorToMajor,
  moneyInputProblem,
  MONEY_INPUT_MESSAGES,
  parseDecimalInput,
} from "@/lib/format";

export type DepositSettingsView = Schema<"DepositSettingsView">;
export type DepositPolicyView = Schema<"DepositPolicyView">;
type DepositRule = Schema<"DepositRule">;
export type DepositStatus = Schema<"DepositStatus">;
export type DepositReport = Schema<"DepositReport">;
export type PaymentLinkView = Schema<"PaymentLinkView">;
export type PaymentLinkKind = Schema<"PaymentLinkKind">;
export type BookingDepositView = Schema<"BookingDepositView">;
export type DepositPolicyBody = RequestBody<"/v1/businesses/{business_id}/deposit-settings/policies", "put">;
export type DepositSettingsBody = RequestBody<"/v1/businesses/{business_id}/deposit-settings", "put">;
export type PaymentLinkBody = RequestBody<"/v1/businesses/{business_id}/deposit-settings/payment-links", "post">;

/** What a policy belongs to: one resource, one service, or the banquet requests. */
export type PolicyTarget =
  | { target: "resource"; resourceId: string }
  | { target: "service"; serviceItemId: string }
  | { target: "banquet" };

export const POLICY_RULES = ["none", "fixed", "per_guest", "percent_of_value"] as const;
export type PolicyRuleChoice = (typeof POLICY_RULES)[number];

export const RULE_LABELS: Record<PolicyRuleChoice, MessageKey> = {
  none: "deposits.policy.rules.none",
  fixed: "deposits.policy.rules.fixed",
  per_guest: "deposits.policy.rules.per_guest",
  percent_of_value: "deposits.policy.rules.percent_of_value",
};

export const DEPOSIT_STATUS: Record<DepositStatus, { label: MessageKey; tone: BadgeTone }> = {
  awaiting: { label: "deposits.status.awaiting", tone: "warning" },
  paid: { label: "deposits.status.paid", tone: "success" },
  expired: { label: "deposits.status.expired", tone: "danger" },
  cancelled: { label: "deposits.status.cancelled", tone: "neutral" },
  refund_due: { label: "deposits.status.refund_due", tone: "warning" },
  kept: { label: "deposits.status.kept", tone: "neutral" },
};

export const PAYMENT_LINK_KINDS: readonly PaymentLinkKind[] = ["template", "static"];

export interface PolicyForm {
  rule: PolicyRuleChoice;
  /** Major units as typed ("20", "12,50"). */
  amount: string;
  percent: string;
  minPartySize: string;
  /** A payment page's id, or "" for the business's default page. */
  paymentLinkId: string;
}

export type PolicyFormErrors = Partial<Record<"amount" | "percent" | "minPartySize", MessageKey>>;

const MAX_PERCENT = 100;

/** The stored policy of a target, if it has one. */
export function policyOf(settings: DepositSettingsView | undefined, target: PolicyTarget): DepositPolicyView | null {
  const policies = settings?.policies ?? [];
  return (
    policies.find((policy) => {
      if (policy.target !== target.target) {
        return false;
      }
      if (target.target === "resource") {
        return policy.resource_id === target.resourceId;
      }
      if (target.target === "service") {
        return policy.service_item_id === target.serviceItemId;
      }
      return true;
    }) ?? null
  );
}

export function policyForm(policy: DepositPolicyView | null): PolicyForm {
  if (!policy) {
    return { rule: "none", amount: "", percent: "", minPartySize: "", paymentLinkId: "" };
  }
  const currency = policy.currency_code;
  return {
    rule: policy.rule,
    amount:
      policy.amount_minor === null || policy.amount_minor === undefined
        ? ""
        : decimalInputValue(minorToMajor(policy.amount_minor, currency), currencyFractionDigits(currency)),
    percent: policy.percent ? String(policy.percent) : "",
    minPartySize: policy.min_party_size ? String(policy.min_party_size) : "",
    paymentLinkId: policy.payment_link_id ?? "",
  };
}

/**
 * The pages a rule may name: a page that fills in the amount fits every
 * rule, a page with one fixed amount only a fixed deposit (the API refuses
 * the rest).
 */
export function pagesForRule(links: readonly PaymentLinkView[], rule: PolicyRuleChoice): PaymentLinkView[] {
  return links.filter((link) => link.kind === "template" || rule === "fixed");
}

function wholeNumber(text: string): number | null {
  const trimmed = text.trim();
  return /^\d+$/.test(trimmed) ? Number(trimmed) : null;
}

/** What is wrong with the form, field by field (nothing for "No deposit"). */
export function policyFormErrors(form: PolicyForm, currency: string): PolicyFormErrors {
  const errors: PolicyFormErrors = {};
  if (form.rule === "none") {
    return errors;
  }
  if (form.rule === "percent_of_value") {
    const percent = wholeNumber(form.percent);
    if (percent === null || percent < 1 || percent > MAX_PERCENT) {
      errors.percent = "deposits.policy.errors.percent";
    }
  } else {
    const problem = form.amount.trim() === "" ? "number" : moneyInputProblem(form.amount, currency);
    const major = parseDecimalInput(form.amount, currency);
    if (problem !== null) {
      errors.amount = MONEY_INPUT_MESSAGES[problem];
    } else if (major === null || majorToMinor(major, currency) < 1) {
      errors.amount = "validation.number";
    }
  }
  if (form.minPartySize.trim() !== "") {
    const size = wholeNumber(form.minPartySize);
    if (size === null || size < 1) {
      errors.minPartySize = "deposits.policy.errors.minParty";
    }
  }
  return errors;
}

/** The PUT body: the target and its policy (null removes it). Check `policyFormErrors` first. */
export function policyRequestBody(
  form: PolicyForm,
  target: PolicyTarget,
  currency: string,
  links: readonly PaymentLinkView[] = [],
): DepositPolicyBody {
  const where =
    target.target === "resource"
      ? { target: target.target, resource_id: target.resourceId }
      : target.target === "service"
        ? { target: target.target, service_item_id: target.serviceItemId }
        : { target: target.target };
  if (form.rule === "none") {
    return { ...where, policy: null };
  }
  const minPartySize = wholeNumber(form.minPartySize);
  const page = pagesForRule(links, form.rule).find((link) => link.id === form.paymentLinkId);
  return {
    ...where,
    policy: {
      rule: form.rule,
      amount_minor:
        form.rule === "percent_of_value" ? null : majorToMinor(parseDecimalInput(form.amount, currency) ?? 0, currency),
      percent: form.rule === "percent_of_value" ? wholeNumber(form.percent) : null,
      min_party_size: minPartySize !== null && minPartySize > 0 ? minPartySize : null,
      payment_link_id: page ? page.id : null,
    },
  };
}

/** A policy in one line: its message, the values it needs, and "from N guests" when it has a threshold. */
export function policySummary(policy: DepositPolicyView): {
  key: MessageKey;
  amountMinor: number | null;
  percent: number | null;
  fromGuests: number | null;
} {
  const keys: Record<DepositRule, MessageKey> = {
    fixed: "deposits.policy.summary.fixed",
    per_guest: "deposits.policy.summary.per_guest",
    percent_of_value: "deposits.policy.summary.percent_of_value",
  };
  return {
    key: keys[policy.rule],
    amountMinor: policy.amount_minor ?? null,
    percent: policy.percent ?? null,
    fromGuests: policy.min_party_size ?? null,
  };
}

/** Staff mark a deposit paid only while it waits for the payment. */
export function canMarkPaid(deposit: BookingDepositView | null | undefined): boolean {
  return deposit?.status === "awaiting";
}

/**
 * The booking as it reads once its deposit is paid: a booking held for the
 * deposit is confirmed (the API does the same); any other status stays.
 */
export function bookingAfterPaid(booking: BookingView): BookingView {
  const isHeld = booking.status === "pending" || booking.status === "pending_deposit";
  return {
    ...booking,
    status: isHeld && booking.deposit ? "confirmed" : booking.status,
    deposit: booking.deposit ? { ...booking.deposit, status: "paid" } : booking.deposit,
  };
}

export type NoShowRateView = Schema<"NoShowRate">;

/**
 * One group's no-shows as the report says them: the share and its counts
 * once the group is large enough, otherwise how far it is from enough
 * (a share of a handful of visits would mislead).
 */
export type NoShowLine =
  | { kind: "rate"; percent: number; noShows: number; finished: number }
  | { kind: "notEnough"; finished: number; min: number };

export function noShowLine(rate: NoShowRateView, minSample: number): NoShowLine {
  if (!rate.has_enough_data || rate.no_show_percent === null || rate.no_show_percent === undefined) {
    return { kind: "notEnough", finished: rate.finished_count, min: minSample };
  }
  return { kind: "rate", percent: rate.no_show_percent, noShows: rate.no_show_count, finished: rate.finished_count };
}

/** Whether the report has anything to show: deposits on, or some asked in the window. */
export function hasDepositActivity(report: DepositReport): boolean {
  return report.is_enabled || report.requested_count > 0;
}
