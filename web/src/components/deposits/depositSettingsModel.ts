/**
 * Settings → Deposits as pure functions: the owner's choices as an
 * autosaving form (on or off, how long a place waits for the payment, the
 * refund window) and a new payment page as a form, with what is wrong
 * with each field before anything is sent.
 */

import type { MessageKey } from "@/i18n/translate";

import type { DepositSettingsBody, DepositSettingsView, PaymentLinkBody, PaymentLinkKind } from "./depositModel";

export const HOLD_MINUTES = { min: 15, max: 1440 } as const;
export const REFUND_HOURS = { min: 0, max: 720 } as const;
const MAX_LABEL_LENGTH = 80;

export interface DepositSettingsForm {
  isEnabled: boolean;
  /** Whole minutes as typed. */
  holdMinutes: string;
  /** Whole hours as typed. */
  refundHours: string;
}

export type DepositSettingsErrors = Partial<Record<"holdMinutes" | "refundHours", MessageKey>>;

export function depositSettingsForm(view: DepositSettingsView): DepositSettingsForm {
  return {
    isEnabled: view.is_enabled,
    holdMinutes: String(view.hold_minutes),
    refundHours: String(view.refund_cutoff_hours),
  };
}

function wholeIn(text: string, range: { min: number; max: number }): number | null {
  const trimmed = text.trim();
  if (!/^\d+$/.test(trimmed)) {
    return null;
  }
  const value = Number(trimmed);
  return value >= range.min && value <= range.max ? value : null;
}

export function depositSettingsErrors(form: DepositSettingsForm): DepositSettingsErrors {
  const errors: DepositSettingsErrors = {};
  if (wholeIn(form.holdMinutes, HOLD_MINUTES) === null) {
    errors.holdMinutes = "deposits.settings.errors.hold";
  }
  if (wholeIn(form.refundHours, REFUND_HOURS) === null) {
    errors.refundHours = "deposits.settings.errors.refund";
  }
  return errors;
}

/** The PUT body for what changed from `base` (the default page stays as it is), or null when nothing did. */
export function depositSettingsBody(form: DepositSettingsForm, base: DepositSettingsView): DepositSettingsBody | null {
  const holdMinutes = wholeIn(form.holdMinutes, HOLD_MINUTES) ?? base.hold_minutes;
  const refundHours = wholeIn(form.refundHours, REFUND_HOURS) ?? base.refund_cutoff_hours;
  if (form.isEnabled === base.is_enabled && holdMinutes === base.hold_minutes && refundHours === base.refund_cutoff_hours) {
    return null;
  }
  return { is_enabled: form.isEnabled, hold_minutes: holdMinutes, refund_cutoff_hours: refundHours, default_payment_link_id: null };
}

/** The body that makes a page the default one, keeping every other choice. */
export function defaultPageBody(view: DepositSettingsView, linkId: string): DepositSettingsBody {
  return {
    is_enabled: view.is_enabled,
    hold_minutes: view.hold_minutes,
    refund_cutoff_hours: view.refund_cutoff_hours,
    default_payment_link_id: linkId,
  };
}

export interface PaymentLinkForm {
  label: string;
  kind: PaymentLinkKind;
  address: string;
}

export type PaymentLinkErrors = Partial<Record<keyof PaymentLinkForm, MessageKey>>;

export const EMPTY_PAYMENT_LINK: PaymentLinkForm = { label: "", kind: "template", address: "" };

/**
 * What is wrong before sending: a name, and a link that starts with
 * https:// (with {amount} or {amount_minor} for a page that fills it in).
 * The API checks the rest and says why in its refusal.
 */
export function paymentLinkErrors(form: PaymentLinkForm): PaymentLinkErrors {
  const errors: PaymentLinkErrors = {};
  const label = form.label.trim();
  if (label === "" || label.length > MAX_LABEL_LENGTH) {
    errors.label = "deposits.pages.errors.label";
  }
  const address = form.address.trim();
  if (address === "") {
    errors.address = "deposits.pages.errors.address";
  } else if (!address.toLowerCase().startsWith("https://")) {
    errors.address = "deposits.pages.refusals.linkNotHttps";
  } else if (form.kind === "template" && !address.includes("{amount}") && !address.includes("{amount_minor}")) {
    errors.address = "deposits.pages.refusals.templateInvalid";
  }
  return errors;
}

export function paymentLinkBody(form: PaymentLinkForm): PaymentLinkBody {
  return { label: form.label.trim(), kind: form.kind, address: form.address.trim() };
}
