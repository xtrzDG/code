/**
 * What the admin client page's account actions accept before they are sent
 * (the API checks the same): the reason the audit log keeps, the extra
 * trial days, the discount and its last day, the credit amount, the
 * reference of a payment recorded by hand, and which bills are still open.
 */

import type { Schema } from "@/api/types";
import { majorToMinor, moneyInputProblem, parseDecimalInput } from "@/lib/format";

import { shiftDay } from "./metrics";

type AdminInvoice = Schema<"AdminInvoiceView">;

/** The six actions of the menu, in its order. */
export const ACCOUNT_ACTIONS = ["extend", "discount", "credit", "waive", "payment", "plan"] as const;
export type AccountAction = (typeof ACCOUNT_ACTIONS)[number];

/** As the API's `AdminActionReason`. */
export const ADMIN_REASON_MIN = 8;
export const ADMIN_REASON_MAX = 300;
/** As the API's `TrialExtensionDays`. */
export const TRIAL_DAYS_MAX = 60;
/** As the API's `BillingCreditAmountMinor`. */
export const CREDIT_MAX_MINOR = 10_000_000;
/** As the API's `ManualPaymentReference`. */
export const REFERENCE_MAX = 120;
/** A discount runs three years at most (the API's limit). */
export const DISCOUNT_MAX_DAYS = 3 * 366;

/** The reason as sent: no blanks around it. */
export function cleanReason(text: string): string {
  return text.trim();
}

export function isReasonValid(text: string): boolean {
  const reason = cleanReason(text);
  return reason.length >= ADMIN_REASON_MIN && reason.length <= ADMIN_REASON_MAX;
}

/** A whole number typed with digits only, within the bounds; else null. */
export function parseWholeNumber(text: string, min: number, max: number): number | null {
  const typed = text.trim();
  if (!/^\d{1,9}$/.test(typed)) {
    return null;
  }
  const value = Number(typed);
  return value >= min && value <= max ? value : null;
}

export function parseTrialDays(text: string): number | null {
  return parseWholeNumber(text, 1, TRIAL_DAYS_MAX);
}

export function parseDiscountPercent(text: string): number | null {
  return parseWholeNumber(text, 1, 100);
}

/**
 * The discount's last day ("YYYY-MM-DD" from a date field) when it is a
 * real day from today (in the client's time zone) to three years ahead.
 */
export function isDiscountDayValid(day: string, today: string): boolean {
  if (!/^\d{4}-\d{2}-\d{2}$/.test(day) || Number.isNaN(Date.parse(`${day}T00:00:00Z`))) {
    return false;
  }
  if (shiftDay(day, 0) !== day) {
    // Date.parse rolls 2026-02-30 over to March; the calendar has no such day.
    return false;
  }
  return day >= today && day <= shiftDay(today, DISCOUNT_MAX_DAYS);
}

/** The latest day a discount may run to, for the date field's `max`. */
export function lastDiscountDay(today: string): string {
  return shiftDay(today, DISCOUNT_MAX_DAYS);
}

/** Credit typed in the subscription's currency, in minor units; null when it is not an amount above zero. */
export function parseCreditMinor(text: string, currency: string): number | null {
  if (text.trim() === "" || moneyInputProblem(text, currency) !== null) {
    return null;
  }
  const major = parseDecimalInput(text, currency);
  if (major === null) {
    return null;
  }
  const minor = majorToMinor(major, currency);
  return minor >= 1 && minor <= CREDIT_MAX_MINOR ? minor : null;
}

/** The reference as sent: no blanks around it. */
export function cleanReference(text: string): string {
  return text.trim();
}

export function isReferenceValid(text: string): boolean {
  const reference = cleanReference(text);
  return reference.length >= 1 && reference.length <= REFERENCE_MAX;
}

/** Bills a payment recorded by hand can still pay: issued or failed, oldest first. */
export function openInvoices(invoices: readonly AdminInvoice[]): AdminInvoice[] {
  return invoices
    .filter((invoice) => invoice.status === "issued" || invoice.status === "failed")
    .sort((left, right) => left.period_start - right.period_start);
}

/**
 * The actions the client's account takes now: every one needs a
 * subscription; a payment needs an open bill; a waiver a fee not waived yet.
 */
export function availableActions(
  account: Schema<"ClientAccountView"> | null | undefined,
  invoices: readonly AdminInvoice[],
  hasSubscription: boolean,
): AccountAction[] {
  if (!hasSubscription) {
    return [];
  }
  return ACCOUNT_ACTIONS.filter((action) => {
    if (action === "payment") {
      return openInvoices(invoices).length > 0;
    }
    if (action === "waive") {
      return !account?.is_setup_fee_waived;
    }
    return true;
  });
}
