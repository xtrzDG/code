"use client";

/**
 * Why the changes did not reach customers, in plain words, each reason
 * with the page that fixes it; failed checks open the conversations that
 * did not pass.
 */

import Link from "next/link";

import type { Schema } from "@/api/types";
import { IconAlert } from "@/components/icons";
import { buttonClasses } from "@/components/ui";
import { useI18n } from "@/i18n/client";
import { fixPath } from "@/lib/assistant/applyFixes";

export function ApplyAttention({
  businessId,
  view,
  onNavigate,
}: {
  businessId: string;
  view: Schema<"ApplyChangesView">;
  onNavigate: () => void;
}) {
  const { t } = useI18n();
  const reasons = view.attention ?? [];

  return (
    <section aria-labelledby="apply-attention" className="space-y-3 rounded-2xl border border-warning/40 bg-warning-soft/40 p-4">
      <h3 id="apply-attention" className="flex items-center gap-2 text-base font-semibold text-ink">
        <IconAlert className="size-5 shrink-0 text-warning" aria-hidden />
        {t("applyChanges.sheet.attentionTitle")}
      </h3>
      <p className="text-sm text-ink-muted">{t("applyChanges.sheet.attentionText")}</p>
      <ul className="space-y-2">
        {reasons.map((reason) => {
          const href = fixPath(businessId, reason.action, view.assistant_version_id);
          // Plain sentences only: check codes ("booking_out_of_hours") mean nothing to an owner.
          const details = (reason.details ?? []).filter((detail) => /\s/.test(detail.trim()));
          return (
            <li key={reason.code} className="space-y-2 rounded-xl bg-surface/90 p-3">
              <p className="text-sm font-medium text-ink">{reason.message}</p>
              {details.length > 0 ? (
                <ul className="list-disc ps-5 text-xs text-ink-muted">
                  {details.map((detail) => (
                    <li key={detail}>{detail}</li>
                  ))}
                </ul>
              ) : null}
              {href ? (
                <Link href={href} onClick={onNavigate} className={buttonClasses({ variant: "secondary", size: "sm" })}>
                  {reason.action.target === "checks" ? t("applyChanges.sheet.openCheck") : reason.action.label}
                </Link>
              ) : null}
            </li>
          );
        })}
      </ul>
    </section>
  );
}
