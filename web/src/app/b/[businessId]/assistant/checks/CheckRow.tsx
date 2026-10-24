"use client";

/**
 * One of the owner's checks in "My checks": the question, what the answer
 * must do, where the check came from and how it did in the latest
 * "Apply changes" (with the answer it got), "Check now" with its latest
 * outcome, plus change, pause and delete.
 */

import { IconPause, IconPencil, IconPlay, IconTrash } from "@/components/icons";
import { CheckNowPanel } from "@/components/teaching/CheckNowPanel";
import { Badge, Button } from "@/components/ui";
import { useI18n } from "@/i18n/client";
import type { MessageKey } from "@/i18n/translate";
import { checkAnchor } from "@/lib/assistant/ownerChecks";
import { languageName } from "@/lib/format";
import type { CheckView } from "@/lib/teaching";
import {
  checkResultReasons,
  checkResultTone,
  EXPECTATION_LABELS,
  needsExpectedText,
  SOURCE_LABELS,
} from "@/lib/teachingChecks";

const OUTCOME_LABELS: Record<"passed" | "failed" | "errored", MessageKey> = {
  passed: "teaching.checks.passed",
  failed: "teaching.checks.failed",
  errored: "teaching.checks.errored",
};

export function CheckRow({
  check,
  onEdit,
  onToggle,
  onDelete,
}: {
  check: CheckView;
  onEdit: () => void;
  onToggle: () => void;
  onDelete: () => void;
}) {
  const { t, locale } = useI18n();
  const result = check.last_result ?? null;
  const reasons = checkResultReasons(check)
    .map((reason) => t(reason))
    .join(" ");
  const expectation = t(EXPECTATION_LABELS[check.expectation]);

  return (
    <li
      id={checkAnchor(check.id)}
      tabIndex={-1}
      className="scroll-mt-24 space-y-3 rounded-xl border border-line bg-surface p-4 shadow-xs outline-none target:border-accent-solid target:ring-2 target:ring-accent-solid/30 focus-visible:ring-2 focus-visible:ring-focus data-[paused]:opacity-75"
      data-check={check.id}
      data-paused={check.is_active ? undefined : ""}
    >
      <div className="flex flex-wrap items-start justify-between gap-2">
        <p dir="auto" data-user-content className="min-w-0 flex-1 text-sm font-medium break-words text-ink">
          {check.question}
        </p>
        {check.is_active ? null : <Badge>{t("teaching.checks.paused")}</Badge>}
      </div>
      <p className="text-sm text-ink-muted">
        <span>{t("teaching.checks.expectation")} </span>
        <span className="font-medium text-ink">{expectation}</span>
        {needsExpectedText(check.expectation) && check.expected_text ? (
          <>
            {": "}
            <span dir="auto" data-user-content className="rounded bg-surface-muted px-1.5 py-0.5 font-medium break-words text-ink">
              {check.expected_text}
            </span>
          </>
        ) : null}
      </p>
      <div className="flex flex-wrap items-center gap-x-3 gap-y-1 text-xs text-ink-subtle">
        <span>{languageName(check.language, locale)}</span>
        <span aria-hidden>·</span>
        <span>{t(SOURCE_LABELS[check.source])}</span>
      </div>
      <div className="space-y-1.5" data-check-result={result?.outcome ?? "none"}>
        <Badge tone={checkResultTone(check)}>
          {result
            ? t(OUTCOME_LABELS[result.outcome], { number: result.assistant_version_number })
            : t("teaching.checks.notRun")}
        </Badge>
        {reasons ? <p className="text-sm text-danger">{reasons}</p> : null}
        {result?.answer ? (
          <p className="text-sm text-ink-muted">
            <span className="text-ink-subtle">{t("teaching.checks.lastAnswer")}: </span>
            <span dir="auto" data-user-content className="break-words">
              {result.answer}
            </span>
          </p>
        ) : null}
      </div>
      <CheckNowPanel checkId={check.id} question={check.question} lastProbe={check.last_probe} />
      <div className="flex flex-wrap gap-2 border-t border-line pt-3">
        <Button
          size="sm"
          variant="secondary"
          leadingIcon={<IconPencil className="size-4" aria-hidden />}
          onClick={onEdit}
          aria-label={t("teaching.checks.editLabel", { question: check.question })}
        >
          {t("teaching.checks.edit")}
        </Button>
        <Button
          size="sm"
          variant="ghost"
          leadingIcon={
            check.is_active ? <IconPause className="size-4" aria-hidden /> : <IconPlay className="size-4" aria-hidden />
          }
          onClick={onToggle}
        >
          {t(check.is_active ? "teaching.checks.pause" : "teaching.checks.resume")}
        </Button>
        <Button
          size="sm"
          variant="danger-ghost"
          leadingIcon={<IconTrash className="size-4" aria-hidden />}
          onClick={onDelete}
          aria-label={t("teaching.checks.deleteLabel", { question: check.question })}
        >
          {t("teaching.checks.delete")}
        </Button>
      </div>
    </li>
  );
}
