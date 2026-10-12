"use client";

import { IconShield } from "@/components/icons";
import { Badge } from "@/components/ui";
import { useI18n } from "@/i18n/client";
import type { MessageKey } from "@/i18n/translate";
import {
  CHAIN_VERDICT_TONES,
  chainVerdict,
  type AuditChainProblem,
  type AuditChainStatusView,
  type ChainVerdict,
} from "@/lib/auditChain";
import { cn } from "@/lib/cn";
import { formatNumber } from "@/lib/format";

const STATUS_KEYS: Readonly<Record<ChainVerdict, MessageKey>> = {
  unchecked: "auditChain.status.unchecked",
  intact: "auditChain.status.intact",
  broken: "auditChain.status.broken",
};

const PROBLEM_KEYS: Readonly<Record<AuditChainProblem, MessageKey>> = {
  hash_mismatch: "auditChain.problems.hash_mismatch",
  link_broken: "auditChain.problems.link_broken",
  position_gap: "auditChain.problems.position_gap",
  head_lost: "auditChain.problems.head_lost",
  checkpoint_mismatch: "auditChain.problems.checkpoint_mismatch",
};

/** "it was changed": what the check found wrong with a broken chain. */
export function useChainProblemText() {
  const { t } = useI18n();
  return (problem: AuditChainProblem | null | undefined) => (problem ? t(PROBLEM_KEYS[problem]) : "");
}

/**
 * What the daily tamper check found in one audit log: the verdict, when it
 * ran, how far it got and where a retention purge left off. `formatWhen`
 * writes the check's time in the reader's zone (the business's on its own
 * Audit tab, the admin's on the admin page).
 */
export function AuditChainSummary({
  view,
  title,
  formatWhen,
  className,
}: {
  view: AuditChainStatusView | null | undefined;
  title?: string;
  formatWhen: (micros: number) => string;
  className?: string;
}) {
  const { t, locale } = useI18n();
  const problemText = useChainProblemText();
  const verdict = chainVerdict(view);
  const position = (value: number) => formatNumber(value, locale);
  const details = [
    view?.verified_through_position ? t("auditChain.verifiedThrough", { position: position(view.verified_through_position) }) : null,
    view?.purged_through_position ? t("auditChain.purgedThrough", { position: position(view.purged_through_position) }) : null,
  ].filter((line): line is string => line !== null);

  return (
    <div className={cn("flex gap-3", className)}>
      <IconShield className={cn("mt-0.5 size-5 shrink-0", verdict === "broken" ? "text-danger" : "text-ink-subtle")} aria-hidden />
      <div className="min-w-0 flex-1 space-y-1">
        <div className="flex flex-wrap items-center gap-x-3 gap-y-1">
          <span className="text-sm font-medium text-ink">{title ?? t("auditChain.title")}</span>
          <Badge tone={CHAIN_VERDICT_TONES[verdict]}>{t(STATUS_KEYS[verdict])}</Badge>
          {view?.checked_at ? (
            <span className="text-xs text-ink-subtle">{t("auditChain.checkedAt", { when: formatWhen(view.checked_at) })}</span>
          ) : null}
        </div>
        <p className={cn("text-sm", verdict === "broken" ? "text-danger" : "text-ink-muted")} role={verdict === "broken" ? "alert" : undefined}>
          {verdict === "broken"
            ? t("auditChain.verdict.broken", {
                position: view?.broken_position ? position(view.broken_position) : "—",
                problem: problemText(view?.problem),
              })
            : t(verdict === "intact" ? "auditChain.verdict.intact" : "auditChain.verdict.unchecked")}
        </p>
        {details.length > 0 ? <p className="text-xs text-ink-subtle">{details.join(" · ")}</p> : null}
      </div>
    </div>
  );
}
