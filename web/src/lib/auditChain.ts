/**
 * The daily tamper check of an audit log (GET …/audit-log/chain and
 * /v1/admin/audit-log/chains): every entry is sealed with the one before
 * it, and the check walks the chain once a day. Pure helpers shared by
 * the owner's Audit tab and the platform admin's Audit page.
 */

import type { Schema } from "@/api/types";
import type { BadgeTone } from "@/components/ui";

export type AuditChainStatusView = Schema<"AuditChainStatusView">;
export type AuditChainProblem = Schema<"AuditChainProblem">;

/**
 * What the latest check found: "unchecked" until the first one ran,
 * "unsealed" while the log holds no sealed entry (only entries from before
 * sealing began, or none), then "intact" or "broken".
 */
export type ChainVerdict = "unchecked" | "unsealed" | "intact" | "broken";

export function chainVerdict(
  view: Pick<AuditChainStatusView, "status" | "verified_through_position"> | null | undefined,
): ChainVerdict {
  if (!view?.status) {
    return "unchecked";
  }
  if (view.status === "broken") {
    return "broken";
  }
  return view.verified_through_position ? "intact" : "unsealed";
}

export const CHAIN_VERDICT_TONES: Readonly<Record<ChainVerdict, BadgeTone>> = {
  unchecked: "neutral",
  unsealed: "neutral",
  intact: "success",
  broken: "danger",
};

