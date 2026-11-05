/**
 * How a line of a client's timeline reads: its headline (what happened)
 * and the facts under it (the bill's number, the discount, how a payment
 * came, the monthly price, the credit, the health issues). Pure: the
 * words of plans, statuses, channels and audit actions come from the
 * caller, so the same mapping serves every language and the tests.
 */

import type { Schema } from "@/api/types";
import type { MessageKey, MessageValues } from "@/i18n/translate";

export type TimelineEntry = Schema<"ClientTimelineEntry">;
export type TimelineKind = Schema<"ClientTimelineKind">;
type TimelineEvent = Schema<"ClientTimelineEvent">;
type Money = Schema<"Money">;

export interface TimelineWords {
  t: (key: MessageKey, values?: MessageValues) => string;
  money: (money: Money) => string;
  percent: (percent: number) => string;
  plan: (plan: Schema<"PlanKey">) => string;
  health: (status: Schema<"ClientHealthStatus">) => string;
  issue: (issue: Schema<"ClientHealthIssue">) => string;
  channel: (channel: Schema<"ChannelKind">) => string;
  auditAction: (action: Schema<"AuditAction">) => string;
  auditEntity: (entity: string) => string;
}

export const TIMELINE_KIND_LABELS: Record<TimelineKind, MessageKey> = {
  admin_action: "adminStory.timeline.kinds.admin_action",
  support: "adminStory.timeline.kinds.support",
  change: "adminStory.timeline.kinds.change",
  billing: "adminStory.timeline.kinds.billing",
  health: "adminStory.timeline.kinds.health",
  milestone: "adminStory.timeline.kinds.milestone",
  onboarding: "adminStory.timeline.kinds.onboarding",
};

const EVENT_TEXTS: Record<TimelineEvent, MessageKey> = {
  audit_entry: "adminStory.timeline.events.audit_entry",
  invoice_issued: "adminStory.timeline.events.invoice_issued",
  invoice_paid: "adminStory.timeline.events.invoice_paid",
  invoice_failed: "adminStory.timeline.events.invoice_failed",
  credit_used: "adminStory.timeline.events.credit_used",
  trial_started: "adminStory.timeline.events.trial_started",
  subscribed: "adminStory.timeline.events.subscribed",
  plan_changed: "adminStory.timeline.events.plan_changed",
  cancelled: "adminStory.timeline.events.cancelled",
  payment_failed: "adminStory.timeline.events.payment_failed",
  health_changed: "adminStory.timeline.events.health_changed",
  business_created: "adminStory.timeline.events.business_created",
  launch_succeeded: "adminStory.timeline.events.launch_succeeded",
  launch_blocked: "adminStory.timeline.events.launch_blocked",
  dpa_accepted: "adminStory.timeline.events.dpa_accepted",
  channel_connected: "adminStory.timeline.events.channel_connected",
  test_chat_tried: "adminStory.timeline.events.test_chat_tried",
  went_live: "adminStory.timeline.events.went_live",
  first_real_conversation: "adminStory.timeline.events.first_real_conversation",
  first_booking: "adminStory.timeline.events.first_booking",
  first_handoff: "adminStory.timeline.events.first_handoff",
  onboarding_requested: "adminStory.timeline.events.onboarding_requested",
};

/** Events whose amount is the subscription's monthly price, not a bill's. */
const MONTHLY_EVENTS: ReadonlySet<TimelineEvent> = new Set(["trial_started", "subscribed", "plan_changed"]);
const NO_VALUE = "—";

/** What happened, in one sentence. */
export function timelineHeadline(entry: TimelineEntry, words: TimelineWords): string {
  const plan = entry.plan_key ? words.plan(entry.plan_key) : NO_VALUE;
  const values: MessageValues = {
    action: entry.audit_action ? words.auditAction(entry.audit_action) : NO_VALUE,
    entity: entry.audit_entity ? words.auditEntity(entry.audit_entity) : NO_VALUE,
    amount: entry.amount ? words.money(entry.amount) : NO_VALUE,
    plan,
    previous: entry.previous_plan_key ? words.plan(entry.previous_plan_key) : NO_VALUE,
    from: entry.health_from ? words.health(entry.health_from) : NO_VALUE,
    to: entry.health_to ? words.health(entry.health_to) : NO_VALUE,
    channel: entry.channel ? words.channel(entry.channel) : NO_VALUE,
  };
  return words.t(EVENT_TEXTS[entry.event], values);
}

/** The facts under the headline, each a short phrase. */
export function timelineDetails(entry: TimelineEntry, words: TimelineWords): string[] {
  const details: string[] = [];
  if (entry.invoice_number) {
    details.push(words.t("adminStory.timeline.invoiceNumber", { number: entry.invoice_number }));
  }
  if (entry.discount_percent) {
    details.push(words.t("adminStory.timeline.discount", { percent: words.percent(entry.discount_percent) }));
  }
  if (entry.payment_method) {
    details.push(words.t(`adminStory.timeline.paidBy.${entry.payment_method}`));
  }
  if (entry.amount && MONTHLY_EVENTS.has(entry.event)) {
    details.push(words.t("adminStory.timeline.monthly", { amount: words.money(entry.amount) }));
  }
  if (entry.amount && entry.event === "audit_entry") {
    // An admin's grant of credit names its amount.
    details.push(words.t("adminStory.timeline.creditAmount", { amount: words.money(entry.amount) }));
  }
  const issues = entry.health_issues ?? [];
  if (issues.length > 0) {
    details.push(words.t("adminStory.timeline.issues", { issues: issues.map(words.issue).join(", ") }));
  }
  return details;
}

/** Badge tone of a line's kind: admin actions stand out, health by where it went. */
export function timelineTone(entry: TimelineEntry): "accent" | "neutral" | "info" | "warning" | "danger" | "success" {
  if (entry.kind === "health") {
    return entry.health_to === "critical" ? "danger" : entry.health_to === "attention" ? "warning" : "success";
  }
  if (entry.kind === "admin_action") {
    return "accent";
  }
  if (entry.kind === "billing") {
    return entry.event === "invoice_failed" || entry.event === "payment_failed" ? "danger" : "info";
  }
  return "neutral";
}
