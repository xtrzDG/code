/**
 * The workers' circuit breakers (GET /v1/admin/system `circuits`) as the
 * System page reads them: which provider a circuit guards, how its state
 * reads, and how many of them want a look. Pure functions, so the card and
 * the tests share them.
 */

import type { Schema } from "@/api/types";
import type { BadgeTone } from "@/components/ui";

export type CircuitSummary = Schema<"CircuitSummaryView">;
export type CircuitState = Schema<"CircuitState">;

/** The providers the platform sends through (`provider:<name>` circuits). */
const CIRCUIT_PROVIDERS = ["meta", "telegram", "platform_bot", "twilio_sms", "smtp", "flitt", "web_push"] as const;
export type CircuitProvider = (typeof CIRCUIT_PROVIDERS)[number];

const PROVIDER_PREFIX = "provider:";

export const CIRCUIT_STATE_TONES: Readonly<Record<CircuitState, BadgeTone>> = {
  open: "danger",
  half_open: "warning",
  closed: "success",
};

/** The provider a circuit guards; null for another circuit (a language model's), shown by its name. */
export function circuitProvider(circuit: string): CircuitProvider | null {
  if (!circuit.startsWith(PROVIDER_PREFIX)) {
    return null;
  }
  const name = circuit.slice(PROVIDER_PREFIX.length);
  return CIRCUIT_PROVIDERS.find((provider) => provider === name) ?? null;
}

/** Circuits that refuse calls or try one: each wants a look. */
export function openCircuitCount(circuits: readonly CircuitSummary[]): number {
  return circuits.filter((circuit) => circuit.state !== "closed").length;
}
