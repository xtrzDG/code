/**
 * Small pure pieces of two-factor sign-in in the cabinet: typed codes,
 * the authenticator key shown in groups, the file of recovery codes, and
 * which text a refused code gets.
 */

import { isApiError, type ApiError } from "@/api/errors";
import type { MessageKey } from "@/i18n/translate";
import { toAsciiDigits } from "@/lib/countries";

export const ONE_TIME_CODE_LENGTH = 6;
/** What a recovery code looks like (letters without look-alikes, and digits). */
export const RECOVERY_CODE_EXAMPLE = "k7mq-2xfp-9hrt";

/** Digits of a typed authenticator code (any keyboard's digits), at most six. */
export function oneTimeCodeDigits(typed: string): string {
  return toAsciiDigits(typed).replace(/\D/g, "").slice(0, ONE_TIME_CODE_LENGTH);
}

export function isCompleteOneTimeCode(code: string): boolean {
  return new RegExp(`^\\d{${ONE_TIME_CODE_LENGTH}}$`).test(code);
}

/** The Base32 key in groups of four, easier to type by hand. */
export function groupedKey(secret: string): string {
  return secret.match(/.{1,4}/g)?.join(" ") ?? secret;
}

/** The downloaded file: a heading line, then one code per line. */
export function recoveryCodesFile(
  heading: string,
  codes: readonly string[],
): string {
  return [heading, "", ...codes, ""].join("\n");
}

export function hasReason(error: unknown, code: string): boolean {
  return (
    isApiError(error) && error.reasons.some((reason) => reason.code === code)
  );
}

/**
 * The text of a refused second factor: a wrong (or used) code, a sign-in
 * step that expired, or too many tries; null for other failures (a toast).
 */
export function secondFactorProblem(error: ApiError): MessageKey | null {
  if (hasReason(error, "wrong_code")) {
    return "mfa.errors.wrongCode";
  }
  if (error.status === 401) {
    return "mfa.errors.expired";
  }
  if (error.status === 429) {
    return "mfa.errors.tooManyAttempts";
  }
  if (error.code === "validation_failed") {
    return "mfa.errors.wrongCode";
  }
  return null;
}
