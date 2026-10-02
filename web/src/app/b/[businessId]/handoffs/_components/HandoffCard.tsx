"use client";

import { useBusiness, useBusinessFormat } from "@/components/business/BusinessContext";
import { IconCheck } from "@/components/icons";
import { HandoffStatusBadge, HandoffUrgencyBadge, TestBadge } from "@/components/insights/Badges";
import { CustomerName, PhoneLink } from "@/components/insights/common";
import { formatRelative } from "@/components/insights/dates";
import { isOpenHandoff } from "@/components/insights/handoffs";
import { HANDOFF_REASONS } from "@/components/insights/labels";
import type { HandoffListItem } from "@/components/insights/types";
import { Button, ButtonLink } from "@/components/ui";
import { useI18n } from "@/i18n/client";
import { cn } from "@/lib/cn";
import { businessPath } from "@/lib/navigation";

const URGENCY_EDGE: Record<HandoffListItem["urgency"], string> = {
  critical: "border-l-danger-solid",
  high: "border-l-warning",
  normal: "border-l-info",
  low: "border-l-line-strong",
};

/** One handoff: why, how urgent, the summary, whom to call back, and "resolve". */
export function HandoffCard({ handoff, onResolve }: { handoff: HandoffListItem; onResolve: () => void }) {
  const { t, locale } = useI18n();
  const { business } = useBusiness();
  const format = useBusinessFormat();
  const open = isOpenHandoff(handoff);
  const headingId = `handoff-${handoff.id}`;

  return (
    <li>
      <article
        aria-labelledby={headingId}
        className={cn(
          "rounded-2xl border border-line bg-surface p-4 shadow-sm sm:p-5",
          open && cn("border-l-4", URGENCY_EDGE[handoff.urgency]),
        )}
      >
        <div className="flex flex-wrap items-center gap-2">
          <h2 id={headingId} className="text-base font-semibold text-ink">
            {t(HANDOFF_REASONS[handoff.reason])}
          </h2>
          {open ? <HandoffUrgencyBadge urgency={handoff.urgency} /> : null}
          <HandoffStatusBadge status={handoff.status} />
          {handoff.is_sandbox ? <TestBadge /> : null}
          <span className="text-xs text-ink-subtle sm:ml-auto">
            <time dateTime={new Date(handoff.created_at / 1000).toISOString()} title={format.dateTime(handoff.created_at)}>
              {formatRelative(handoff.created_at, locale) ?? format.dateTime(handoff.created_at)}
            </time>
          </span>
        </div>

        <p dir="auto" className="mt-2 text-sm whitespace-pre-wrap text-ink">
          {handoff.summary}
        </p>

        {handoff.status === "notification_failed" ? (
          <p className="mt-2 text-sm text-danger">{t("handoffs.notificationFailedHint")}</p>
        ) : null}

        <div className="mt-4 flex flex-col gap-3 border-t border-line pt-3 sm:flex-row sm:items-center sm:justify-between">
          <p className="flex flex-wrap items-center gap-x-3 gap-y-1 text-sm">
            <span className="font-medium text-ink">
              <CustomerName name={handoff.contact_name} />
            </span>
            {handoff.contact_phone_number ? <PhoneLink phone={handoff.contact_phone_number} /> : null}
            {!open && handoff.resolved_at ? (
              <span className="text-ink-muted">{t("handoffs.resolvedAt", { date: format.dateTime(handoff.resolved_at) })}</span>
            ) : null}
          </p>
          <div className="flex flex-wrap gap-2">
            <ButtonLink
              href={`${businessPath(business.id, "conversations")}/${encodeURIComponent(handoff.conversation_id)}`}
              variant="secondary"
              size="sm"
            >
              {t("insights.openConversation")}
            </ButtonLink>
            {open ? (
              <Button size="sm" leadingIcon={<IconCheck className="size-4" aria-hidden />} onClick={onResolve}>
                {t("handoffs.resolve")}
              </Button>
            ) : null}
          </div>
        </div>
      </article>
    </li>
  );
}
