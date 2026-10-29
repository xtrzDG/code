"use client";

import { api } from "@/api/client";
import { queryKeys } from "@/api/queryKeys";
import type { Schema } from "@/api/types";
import { useCursorPage } from "@/api/useCursorPage";
import { Badge, Button, Card, ErrorState, InlineError, SkeletonRows, UserSentence } from "@/components/ui";
import { CHANNEL_NAMES } from "@/components/workspace/channelNames";
import { useI18n } from "@/i18n/client";
import { formatNumber } from "@/lib/format";

import {
  TIMELINE_KIND_LABELS,
  timelineDetails,
  timelineHeadline,
  timelineTone,
  type TimelineEntry,
  type TimelineWords,
} from "../../../_lib/timeline";
import { useClientFormat } from "../../../_lib/useClientFormat";
import { HEALTH_LABELS, ISSUE_LABELS, PLAN_LABELS } from "../../labels";

const TIMELINE_PAGE_SIZE = 30;

/**
 * A line's identity across pages (lines have no id of their own): two
 * channels connected in the same moment are two lines.
 */
function lineKey(entry: TimelineEntry): string {
  return [
    entry.occurred_at,
    entry.kind,
    entry.event,
    entry.audit_action,
    entry.audit_entity,
    entry.invoice_number,
    entry.actor_user_id,
    entry.channel,
    entry.plan_key,
    entry.previous_plan_key,
    entry.health_to,
    entry.amount?.amount_minor,
  ]
    .map((part) => part ?? "")
    .join("|");
}

/**
 * The client's story, newest first, 30 lines at a time: the audit log
 * (views and sign-ins left out), bills and credit, the subscription's
 * steps, health changes, the setup's milestones and the done-for-you
 * request, each with who did it and, for an admin's action, why.
 */
export function TimelineCard({ businessId, timeZone }: { businessId: string; timeZone: string }) {
  const { t, tDynamic, locale } = useI18n();
  const { dateTime, money } = useClientFormat(timeZone);
  const timeline = useCursorPage<TimelineEntry, Schema<"ClientTimelinePage">>(
    queryKeys.admin.clientTimeline(businessId),
    ({ cursor, limit }) =>
      api.GET("/v1/admin/clients/{business_id}/timeline", {
        params: { path: { business_id: businessId }, query: { limit: String(limit), ...(cursor ? { cursor } : {}) } },
      }),
    { pageSize: TIMELINE_PAGE_SIZE, itemKey: lineKey },
  );
  const words: TimelineWords = {
    t,
    money: (amount) => money(amount.amount_minor, amount.currency_code),
    percent: (percent) => formatNumber(percent / 100, locale, { style: "percent" }),
    plan: (plan) => t(PLAN_LABELS[plan]),
    health: (status) => t(HEALTH_LABELS[status]),
    issue: (issue) => t(ISSUE_LABELS[issue]),
    channel: (channel) => t(CHANNEL_NAMES[channel]),
    auditAction: (action) => tDynamic(`settings.audit.actions.${action}`, action),
    auditEntity: (entity) => tDynamic(`settings.audit.entities.${entity.replaceAll(".", "_")}`, entity),
  };
  // Who did it: a person's name is user content ("System" is ours).
  const actor = (entry: TimelineEntry) =>
    entry.actor_name ? (
      <UserSentence text={t("adminStory.timeline.by")} values={{ name: entry.actor_name }} />
    ) : entry.actor_user_id || entry.event !== "audit_entry" ? null : (
      t("adminStory.timeline.by", { name: t("adminStory.timeline.system") })
    );
  const items = timeline.items;

  return (
    <Card title={t("adminStory.timeline.title")} description={t("adminStory.timeline.description")} aria-label={t("adminStory.timeline.title")}>
      {timeline.error && !items ? (
        <ErrorState error={timeline.error} onRetry={timeline.reload} />
      ) : !items ? (
        <SkeletonRows rows={4} />
      ) : items.length === 0 ? (
        <p className="text-sm text-ink-muted">{t("adminStory.timeline.empty")}</p>
      ) : (
        <>
          <ol className="relative space-y-4 border-s border-line ps-5">
            {items.map((entry) => {
              const details = timelineDetails(entry, words);
              const by = actor(entry);
              return (
                <li key={lineKey(entry)} className="relative">
                  <span aria-hidden className="absolute top-1.5 -start-[1.6rem] size-2.5 rounded-full border-2 border-surface bg-line-strong" />
                  <div className="flex flex-wrap items-center gap-2">
                    <Badge tone={timelineTone(entry)}>{t(TIMELINE_KIND_LABELS[entry.kind])}</Badge>
                    <time className="text-xs text-ink-subtle" dateTime={new Date(entry.occurred_at / 1000).toISOString()}>
                      {dateTime(entry.occurred_at)}
                    </time>
                  </div>
                  <p className="mt-1 text-sm font-medium break-words text-ink">{timelineHeadline(entry, words)}</p>
                  {details.length > 0 ? <p className="text-xs text-ink-muted">{details.join(" · ")}</p> : null}
                  {entry.reason ? (
                    <p dir="auto" className="mt-1 text-xs break-words text-ink-muted">
                      <UserSentence text={t("adminStory.timeline.reason")} values={{ reason: entry.reason }} />
                    </p>
                  ) : null}
                  {by ? (
                    <p dir="auto" className="mt-0.5 text-xs text-ink-subtle">
                      {by}
                    </p>
                  ) : null}
                </li>
              );
            })}
          </ol>
          {timeline.moreError ? <InlineError className="mt-3" error={timeline.moreError} /> : null}
          {timeline.hasMore ? (
            <Button className="mt-4" size="sm" variant="secondary" isLoading={timeline.isLoadingMore} onClick={timeline.loadMore}>
              {t("adminStory.timeline.loadMore")}
            </Button>
          ) : null}
        </>
      )}
    </Card>
  );
}
