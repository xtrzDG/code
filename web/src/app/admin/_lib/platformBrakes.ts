/**
 * The platform's brakes as the System page shows them: the global pause a
 * SUPER admin sets (every assistant hands customers to the team) and the
 * daily budget stop (the providers' spend of the UTC day reached its stop
 * share), and the latest daily payment reconciliation with Flitt and Stripe.
 */

import type { Schema } from "@/api/types";

export type PlatformBrakes = Schema<"PlatformPauseView">;
export type PaymentReconciliation = Schema<"PaymentReconciliationView">;
export type PaymentMismatch = Schema<"PaymentMismatchView">;

/** How the assistants stand: answering, paused by an admin, or stopped by the budget. */
export type BrakeState = "running" | "paused" | "stopped";

export function brakeState(
  brakes: Pick<PlatformBrakes, "is_paused" | "brake">,
): BrakeState {
  if (brakes.is_paused) {
    return "paused";
  }
  return brakes.brake === "budget_stop" ? "stopped" : "running";
}

export const BRAKE_TONES = {
  running: "success",
  paused: "danger",
  stopped: "danger",
} as const;

/** Whether the reconciliation found payments that differ from the provider. */
export function hasMismatches(
  reconciliation: Pick<PaymentReconciliation, "mismatches">,
): boolean {
  return reconciliation.mismatches.length > 0;
}
