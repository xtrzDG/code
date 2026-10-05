"use client";

/**
 * Why an update did not pass when the owner's own checks are the only
 * thing that failed: "Your check did not pass: “Can I come with my dog?” —
 * the answer must pass the customer to a person", with "Fix the answer"
 * and "Open the check", instead of a bare "Checks failed" next to a good
 * score. Several failed checks are listed one under another.
 */

import { useApplyChanges } from "@/components/assistant/ApplyChangesContext";
import { OwnerCheckFailure } from "@/components/assistant/OwnerCheckFailure";
import { useBusiness } from "@/components/business/BusinessContext";
import { IconAlert } from "@/components/icons";
import { useI18n } from "@/i18n/client";
import { failureSentence, type NamedFailure } from "@/lib/assistant/ownerChecks";

export function OwnerCheckVerdict({ failures }: { failures: readonly NamedFailure[] }) {
  const translator = useI18n();
  const { tp, t } = translator;
  const { business, isOwner } = useBusiness();
  const { fixAnswer } = useApplyChanges();
  if (failures.length === 0) {
    return null;
  }
  return (
    <section
      aria-labelledby="owner-check-verdict"
      className="mt-5 space-y-3 rounded-2xl border border-danger/25 bg-danger-soft/60 p-4"
      data-owner-check-verdict=""
    >
      <h3 id="owner-check-verdict" className="flex items-start gap-2 text-sm font-semibold [overflow-wrap:anywhere] text-danger" dir="auto">
        <IconAlert className="mt-0.5 size-4 shrink-0" aria-hidden />
        <span>{failures.length === 1 ? failureSentence(failures[0]!, translator) : tp("updates.failed.many", failures.length)}</span>
      </h3>
      {failures.map((failure, index) => (
        <OwnerCheckFailure
          key={failure.checkId ?? failure.question}
          businessId={business.id}
          failure={failure}
          onFixAnswer={isOwner ? fixAnswer : undefined}
          showSentence={failures.length > 1}
          className={index > 0 ? "border-t border-danger/15 pt-3" : undefined}
        />
      ))}
      <p className="text-xs text-ink-muted">{t("updates.failed.rest")}</p>
    </section>
  );
}
