"use client";

/**
 * One of the owner's checks that did not pass, named the same way wherever
 * it shows (the "Apply changes" sheet, the update's page): "Your check did
 * not pass: “Can I come with my dog?” — the answer must pass the customer
 * to a person", why in plain words, the test answer, and the two ways to
 * fix it: open the check, or fix the answer it got.
 */

import { IconPencil, IconShield } from "@/components/icons";
import { Button, ButtonLink, UserSentence } from "@/components/ui";
import { useI18n } from "@/i18n/client";
import { checkPath, failureSentence, type NamedFailure } from "@/lib/assistant/ownerChecks";
import { cn } from "@/lib/cn";

export function OwnerCheckFailure({
  businessId,
  failure,
  onFixAnswer,
  onNavigate,
  showSentence = true,
  className,
}: {
  businessId: string;
  failure: NamedFailure;
  /** Opens "Fix this answer" on the test answer; omitted when the viewer cannot fix answers. */
  onFixAnswer?: (failure: NamedFailure) => void;
  /** Called before "Open the check" leaves the page (a sheet closes). */
  onNavigate?: () => void;
  /** False when a heading over it already says the sentence. */
  showSentence?: boolean;
  className?: string;
}) {
  const translator = useI18n();
  const { t } = translator;
  const canFix = onFixAnswer !== undefined && failure.conversationId !== null && failure.answerMessageId !== null;

  return (
    <div className={cn("space-y-2", className)} data-owner-check-failure={failure.checkId ?? ""}>
      {showSentence ? (
        <p dir="auto" className="text-sm font-medium [overflow-wrap:anywhere] text-ink">
          <UserSentence {...failureSentence(failure, translator)} />
        </p>
      ) : null}
      {failure.reason ? <p className="text-sm text-ink-muted">{failure.reason}</p> : null}
      {failure.answer ? (
        <p className="text-sm text-ink-muted">
          <span className="text-ink-subtle">{t("updates.failed.answered")}: </span>
          <span dir="auto" data-user-content className="line-clamp-3 [overflow-wrap:anywhere]">
            {failure.answer}
          </span>
        </p>
      ) : null}
      <div className="flex flex-wrap gap-2 pt-1">
        {canFix ? (
          <Button size="sm" leadingIcon={<IconPencil className="size-4" aria-hidden />} onClick={() => onFixAnswer(failure)}>
            {t("updates.failed.fixAnswer")}
          </Button>
        ) : null}
        <ButtonLink
          href={checkPath(businessId, failure.checkId)}
          onClick={onNavigate}
          variant="secondary"
          size="sm"
          leadingIcon={<IconShield className="size-4" aria-hidden />}
        >
          {t("updates.failed.openCheck")}
        </ButtonLink>
      </div>
    </div>
  );
}
