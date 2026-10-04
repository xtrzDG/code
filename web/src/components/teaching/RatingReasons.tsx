"use client";

/**
 * Under a bad rating: what was wrong (wrong information, should have
 * passed it to a person, tone, too long) and, for owners, the way to fix
 * the answer or keep the question as a check.
 */

import { Button } from "@/components/ui";
import { useI18n } from "@/i18n/client";
import { cn } from "@/lib/cn";
import { RATING_REASONS, REASON_LABELS, type RatingReason } from "@/lib/teaching";

export function RatingReasons({
  value,
  isPending,
  onChange,
  onFix,
  onSaveCheck,
}: {
  value: RatingReason | null;
  isPending: boolean;
  onChange: (reason: RatingReason) => void;
  /** Owners: open "Fix this answer" on the rated answer (null: not offered). */
  onFix: (() => void) | null;
  onSaveCheck: (() => void) | null;
}) {
  const { t } = useI18n();
  return (
    <div className="mt-3 space-y-3" data-rating-reasons="">
      <div role="radiogroup" aria-label={t("teaching.rating.reasonLabel")} className="space-y-1.5">
        <p className="text-xs text-ink-muted">{t("teaching.rating.reasonLabel")}</p>
        <div className="flex flex-wrap gap-1.5">
          {RATING_REASONS.map((reason) => {
            const isChosen = value === reason;
            return (
              <button
                key={reason}
                type="button"
                role="radio"
                aria-checked={isChosen}
                aria-busy={isPending || undefined}
                onClick={() => onChange(reason)}
                className={cn(
                  "min-h-9 rounded-full border px-3 text-sm transition-colors focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-focus",
                  isChosen
                    ? "border-danger/40 bg-danger-soft font-medium text-danger"
                    : "border-line bg-surface text-ink-muted hover:border-line-strong hover:text-ink",
                )}
              >
                {t(REASON_LABELS[reason])}
              </button>
            );
          })}
        </div>
      </div>
      {onFix || onSaveCheck ? (
        <div className="flex flex-wrap gap-2">
          {onFix ? (
            <Button size="sm" onClick={onFix}>
              {t("teaching.rating.fixAnswer")}
            </Button>
          ) : null}
          {onSaveCheck ? (
            <Button size="sm" variant="secondary" onClick={onSaveCheck}>
              {t("teaching.rating.saveCheck")}
            </Button>
          ) : null}
        </div>
      ) : null}
    </div>
  );
}
