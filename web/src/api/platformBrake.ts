/**
 * The platform holds every assistant's AI work back (409, reason
 * `platform_brake`; its detail says which brake: `paused` by a platform
 * admin, or `budget_stop` for the rest of the day): menu import, autotest
 * runs, name suggestions, phone number rental and website import are
 * refused and nothing is started. Every screen words it alike
 * (`describeError` in errors.ts reads SHARED_REASON_MESSAGES after the
 * screen's own reasons).
 */

import type { MessageKey } from "@/i18n/translate";

import type { ReasonMessages } from "./errors";

export const PLATFORM_BRAKE_REASON = "platform_brake";

/** The words for a platform brake by its detail (`paused`, `budget_stop`; anything else: held back). */
export function platformBrakeText(detail: string | null | undefined): MessageKey {
  if (detail === "paused") {
    return "errors.platformBrake.paused";
  }
  return detail === "budget_stop" ? "errors.platformBrake.budgetStop" : "errors.platformBrake.held";
}

/** Reasons every screen words alike; a screen's own `reasonMessages` come first. */
export const SHARED_REASON_MESSAGES: ReasonMessages = {
  [PLATFORM_BRAKE_REASON]: (reason) => ({ key: platformBrakeText(reason.details[0]) }),
};
