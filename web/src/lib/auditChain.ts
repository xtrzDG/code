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

/** What the latest check found; "unchecked" until the first one ran. */
export type ChainVerdict = "unchecked" | "intact" | "broken";

export function chainVerdict(view: Pick<AuditChainStatusView, "status"> | null | undefined): ChainVerdict {
  if (!view?.status) {
    return "unchecked";
  }
  return view.status === "broken" ? "broken" : "intact";
}

export const CHAIN_VERDICT_TONES: Readonly<Record<ChainVerdict, BadgeTone>> = {
  unchecked: "neutral",
  intact: "success",
  broken: "danger",
};

