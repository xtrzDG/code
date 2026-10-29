"use client";

/**
 * "Check now" and how it went, inline: passed or not with what customers
 * get now, why in plain words, the answer it got and, when it failed,
 * "Fix the answer". Shown under a saved check and on each check of "My
 * checks" (the latest probe while the check is asked the same way).
 */

import { useApplyChanges } from "@/components/assistant/ApplyChangesContext";
import { useBusinessFormat } from "@/components/business/BusinessContext";
import { IconAlert, IconCheckCircle, IconFlask, IconPencil, IconXCircle } from "@/components/icons";
import { Button } from "@/components/ui";
import { useI18n } from "@/i18n/client";
import { namedFailureOfOutcome, type OwnerCheckOutcome } from "@/lib/assistant/ownerChecks";
import { cn } from "@/lib/cn";

import { useCheckNow, type CheckNowProblem } from "./useCheckNow";

const PROBLEM_TEXTS = {
  notLive: "updates.checkNow.notLive",
  limited: "updates.checkNow.limited",
  failed: "updates.checkNow.errored",
} as const satisfies Record<CheckNowProblem, string>;

export function CheckNowPanel({
  checkId,
  question,
  lastProbe,
  showButton = true,
}: {
  checkId: string;
  question: string;
  /** The latest "Check now" kept on the check, shown until a new one runs. */
  lastProbe?: OwnerCheckOutcome | null;
  showButton?: boolean;
}) {
  const { t } = useI18n();
  const checkNow = useCheckNow(checkId);
  const outcome = checkNow.outcome ?? lastProbe ?? null;

  return (
    <div className="space-y-2" data-check-now="">
      {showButton ? (
        <div className="flex flex-wrap items-center gap-x-3 gap-y-1">
          <Button
            size="sm"
            variant="secondary"
            leadingIcon={<IconFlask className="size-4" aria-hidden />}
            isLoading={checkNow.isPending}
            loadingText={t("updates.checkNow.checking")}
            aria-label={t("updates.checkNow.actionLabel", { question })}
            onClick={() => void checkNow.run()}
          >
            {t("updates.checkNow.action")}
          </Button>
          <span className="text-xs text-ink-subtle">{t("updates.checkNow.hint")}</span>
        </div>
      ) : null}
      <div aria-live="polite">
        {checkNow.problem ? (
          <p className="text-sm text-warning" data-check-now-problem={checkNow.problem}>
            {t(PROBLEM_TEXTS[checkNow.problem])}
          </p>
        ) : outcome && !checkNow.isPending ? (
          <CheckNowOutcome outcome={outcome} />
        ) : null}
      </div>
    </div>
  );
}

function CheckNowOutcome({ outcome }: { outcome: OwnerCheckOutcome }) {
  const { t } = useI18n();
  const format = useBusinessFormat();
  const { canApply, fixAnswer } = useApplyChanges();
  const passed = outcome.outcome === "passed";
  const Icon = passed ? IconCheckCircle : outcome.outcome === "failed" ? IconXCircle : IconAlert;
  const failure = namedFailureOfOutcome(outcome);
  const canFix = canApply && !passed && failure.conversationId !== null && failure.answerMessageId !== null;

  return (
    <div
      className={cn(
        "space-y-1.5 rounded-xl border px-3 py-2.5 text-sm",
        passed ? "border-success/30 bg-success-soft/40" : outcome.outcome === "failed" ? "border-danger/25 bg-danger-soft/50" : "border-warning/30 bg-warning-soft/40",
      )}
      data-check-probe={outcome.outcome}
    >
      <p className="flex items-start gap-2 font-medium text-ink">
        <Icon
          className={cn("mt-0.5 size-4 shrink-0", passed ? "text-success" : outcome.outcome === "failed" ? "text-danger" : "text-warning")}
          aria-hidden
        />
        <span>
          {passed ? t("updates.checkNow.passed") : outcome.outcome === "failed" ? t("updates.checkNow.failed") : t("updates.checkNow.errored")}
        </span>
      </p>
      {!passed && outcome.reason ? <p className="text-ink-muted">{outcome.reason}</p> : null}
      {outcome.answer ? (
        <p className="text-ink-muted">
          <span className="text-ink-subtle">{t("updates.failed.answered")}: </span>
          <span dir="auto" data-user-content className="[overflow-wrap:anywhere]">
            {outcome.answer}
          </span>
        </p>
      ) : null}
      <div className="flex flex-wrap items-center justify-between gap-2">
        <span className="text-xs text-ink-subtle">{t("updates.checkNow.checkedAt", { date: format.dateTime(outcome.checked_at) })}</span>
        {canFix ? (
          <Button size="sm" variant="ghost" leadingIcon={<IconPencil className="size-4" aria-hidden />} onClick={() => fixAnswer(failure)}>
            {t("updates.failed.fixAnswer")}
          </Button>
        ) : null}
      </div>
    </div>
  );
}
