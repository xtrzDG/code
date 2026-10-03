/**
 * The two ways of getting the assistant set up (a plan quote's
 * `setup_options`): SELF_SERVE, the owner with the guide on the Overview,
 * free; DONE_FOR_YOU, the platform team, for the plan's one-time setup
 * fee (included in a yearly payment). Chosen when subscribing.
 */

import type { Schema } from "@/api/types";

import { planSetupFee, type BillingPeriod, type PlanQuote, type QuotedMoney, type SubscriptionView } from "./billing";

export type SetupOption = Schema<"SetupOption">;

/** In the order the subscribe dialog offers them: the free one first. */
export const SETUP_OPTIONS: readonly SetupOption[] = ["self_serve", "done_for_you"];

export const DEFAULT_SETUP_OPTION: SetupOption = "self_serve";

/** The fee of an option, in the local currency when known; null when nothing is charged. */
export function setupOptionFee(quote: PlanQuote, option: SetupOption, period: BillingPeriod): QuotedMoney | null {
  if (period === "annual") {
    return null;
  }
  const quoted = (quote.setup_options ?? []).find((item) => item.option === option);
  const fee = quoted ? (quoted.local_fee ?? quoted.fee) : option === "done_for_you" ? planSetupFee(quote) : null;
  return fee && fee.money.amount_minor > 0 ? fee : null;
}

/** How the subscription's business gets set up, as the billing page tells it (null: chosen when subscribing). */
export type SetupState =
  | { kind: "self_serve" }
  | { kind: "done_for_you"; requestedAt: number | null }
  | null;

export function setupState(subscription: SubscriptionView | null | undefined): SetupState {
  if (subscription?.setup_option === "done_for_you") {
    return { kind: "done_for_you", requestedAt: subscription.onboarding_requested_at ?? null };
  }
  return subscription?.setup_option === "self_serve" ? { kind: "self_serve" } : null;
}
