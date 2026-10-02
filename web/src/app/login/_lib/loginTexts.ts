/** Texts and input rules of the sign-in page. */

import { z } from "zod";

import type { OtpDeliveryChannel } from "@/api/types";
import type { MessageKey } from "@/i18n/translate";
import { looksLikeEmail, looksLikePhoneNumber } from "@/lib/countries";
import { messageKey } from "@/lib/validation";

/** The API refuses a second code for the same destination within 30 s. */
export const RESEND_INTERVAL_MS = 30_000;
export const CODE_LENGTH = 6;

export const DELIVERY_CHANNEL_LABELS: Record<OtpDeliveryChannel, MessageKey> = {
  sms: "auth.deliveryChannels.sms",
  whatsapp: "auth.deliveryChannels.whatsapp",
  telegram: "auth.deliveryChannels.telegram",
  email: "auth.deliveryChannels.email",
};

/** The page's own wording for refusals classified by `classifyOtpStartError` / `classifyOtpVerifyError`. */
export const PROBLEM_MESSAGES = {
  countryRestricted: "auth.errors.countryRestricted",
  resendTooSoon: "auth.errors.resendTooSoon",
  cannotReceive: "auth.errors.cannotReceive",
  phoneInvalid: "auth.errors.phoneInvalid",
  emailInvalid: "auth.errors.emailInvalid",
  wrongCode: "auth.errors.wrongCode",
  tooManyAttempts: "auth.errors.tooManyAttempts",
} as const satisfies Record<string, MessageKey>;

export const PhoneSchema = z
  .string()
  .trim()
  .min(1, messageKey("auth.errors.phoneRequired"))
  .refine(looksLikePhoneNumber, messageKey("auth.errors.phoneInvalid"));

export const EmailSchema = z.string().trim().refine(looksLikeEmail, messageKey("auth.errors.emailInvalid"));

export const CodeSchema = z.string().regex(/^\d{6}$/, messageKey("auth.errors.codeInvalid"));
