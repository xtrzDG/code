/**
 * Pure rules of Bookings → Return visits: the owner's form (on or off, the
 * rule and its days, who may get the message, the monthly cap), its checks
 * and the body the API takes, and the labels of rules, statuses and the
 * reasons a message was not sent.
 */

import type { Schema } from "@/api/types";
import type { BadgeTone } from "@/components/ui";
import type { MessageKey, PluralKey } from "@/i18n/translate";

export type CampaignSettingsView = Schema<"CampaignSettingsView">;
export type CampaignMessage = Schema<"CampaignMessageView">;
export type CampaignMessagePage = Schema<"CampaignMessagePage">;
export type RebookingRuleKind = Schema<"RebookingRuleKind">;
export type CampaignAudience = Schema<"CampaignAudience">;
export type CampaignMessageStatus = Schema<"CampaignMessageStatus">;
export type CampaignSkipReason = Schema<"CampaignSkipReason">;

/** What PUT /campaign-settings takes. */
export interface CampaignSettingsBody {
  is_enabled: boolean;
  rule_kind: RebookingRuleKind;
  delay_days: number;
  audience: CampaignAudience;
  segment_id: string | null;
  monthly_cap: number;
}

export const RULE_KINDS = ["rebook", "recall", "pre_arrival"] as const satisfies readonly RebookingRuleKind[];
export const AUDIENCES = ["all_customers", "segment"] as const satisfies readonly CampaignAudience[];

const DELAY_DAYS = { min: 1, max: 730 } as const;
const MONTHLY_CAP = { min: 1, max: 2000 } as const;

export const RULE_LABELS: Record<RebookingRuleKind, MessageKey> = {
  rebook: "returnVisits.rules.rebook",
  recall: "returnVisits.rules.recall",
  pre_arrival: "returnVisits.rules.pre_arrival",
};

export const RULE_HINTS: Record<RebookingRuleKind, MessageKey> = {
  rebook: "returnVisits.ruleHints.rebook",
  recall: "returnVisits.ruleHints.recall",
  pre_arrival: "returnVisits.ruleHints.pre_arrival",
};

export const AUDIENCE_LABELS: Record<CampaignAudience, MessageKey> = {
  all_customers: "returnVisits.settings.audiences.all_customers",
  segment: "returnVisits.settings.audiences.segment",
};

export const MESSAGE_STATUS_LABELS: Record<CampaignMessageStatus, MessageKey> = {
  sent: "returnVisits.messages.status.sent",
  booked: "returnVisits.messages.status.booked",
  skipped: "returnVisits.messages.status.skipped",
};

export const MESSAGE_STATUS_TONES: Record<CampaignMessageStatus, BadgeTone> = {
  sent: "neutral",
  booked: "success",
  skipped: "warning",
};

export const RECENT_LABELS: Record<CampaignMessageStatus, MessageKey> = {
  sent: "returnVisits.recent.sent",
  booked: "returnVisits.recent.booked",
  skipped: "returnVisits.recent.skipped",
};

export const SKIP_REASON_LABELS: Record<CampaignSkipReason, MessageKey> = {
  opted_out: "returnVisits.messages.skipReasons.opted_out",
  no_contact: "returnVisits.messages.skipReasons.no_contact",
  no_channel: "returnVisits.messages.skipReasons.no_channel",
  window_closed: "returnVisits.messages.skipReasons.window_closed",
};

/** A note before arrival counts days before a booking; the others after the last visit. */
function isBeforeArrival(rule: RebookingRuleKind): boolean {
  return rule === "pre_arrival";
}

/** The days field's label for a rule. */
export function daysLabel(rule: RebookingRuleKind): MessageKey {
  return isBeforeArrival(rule) ? "returnVisits.settings.daysBefore" : "returnVisits.settings.daysAfter";
}

/** The line that names the niche's usual rule ("… after 35 days", "… 2 days before"). */
export function suggestionKey(rule: RebookingRuleKind): PluralKey {
  return isBeforeArrival(rule) ? "returnVisits.settings.suggestedBefore" : "returnVisits.settings.suggested";
}

export interface CampaignForm {
  isEnabled: boolean;
  ruleKind: RebookingRuleKind;
  /** As typed: checked before saving. */
  delayDays: string;
  audience: CampaignAudience;
  segmentId: string;
  monthlyCap: string;
}

export function campaignForm(view: CampaignSettingsView): CampaignForm {
  return {
    isEnabled: view.is_enabled,
    ruleKind: view.rule_kind,
    delayDays: String(view.delay_days),
    audience: view.audience,
    segmentId: view.segment_id ?? "",
    monthlyCap: String(view.monthly_cap),
  };
}

/** A whole number within the bounds, or null. */
export function wholeNumber(text: string, bounds: { min: number; max: number }): number | null {
  const trimmed = text.trim();
  if (!/^\d+$/.test(trimmed)) {
    return null;
  }
  const value = Number(trimmed);
  return value >= bounds.min && value <= bounds.max ? value : null;
}

export interface CampaignErrors {
  delayDays: MessageKey | null;
  monthlyCap: MessageKey | null;
  segment: MessageKey | null;
}

export function campaignErrors(form: CampaignForm): CampaignErrors {
  return {
    delayDays: wholeNumber(form.delayDays, DELAY_DAYS) === null ? "returnVisits.settings.errors.days" : null,
    monthlyCap: wholeNumber(form.monthlyCap, MONTHLY_CAP) === null ? "returnVisits.settings.errors.cap" : null,
    segment: form.audience === "segment" && form.segmentId === "" ? "returnVisits.settings.errors.segment" : null,
  };
}

export function hasErrors(errors: CampaignErrors): boolean {
  return Object.values(errors).some((error) => error !== null);
}

/** The body to save; call only for a form without errors. */
export function campaignBody(form: CampaignForm): CampaignSettingsBody {
  return {
    is_enabled: form.isEnabled,
    rule_kind: form.ruleKind,
    delay_days: wholeNumber(form.delayDays, DELAY_DAYS) ?? DELAY_DAYS.min,
    audience: form.audience,
    segment_id: form.audience === "segment" ? form.segmentId : null,
    monthly_cap: wholeNumber(form.monthlyCap, MONTHLY_CAP) ?? MONTHLY_CAP.min,
  };
}

/** Nothing to save: the form says what is stored. */
export function isSameCampaign(form: CampaignForm, view: CampaignSettingsView): boolean {
  const stored = campaignForm(view);
  return (
    form.isEnabled === stored.isEnabled &&
    form.ruleKind === stored.ruleKind &&
    form.delayDays.trim() === stored.delayDays &&
    form.audience === stored.audience &&
    (form.audience === "all_customers" || form.segmentId === stored.segmentId) &&
    form.monthlyCap.trim() === stored.monthlyCap
  );
}

/**
 * The counts of the last 30 days, every status present (0 when none):
 * `sent` is every message that went out, those that led to a booking
 * among them (as the monthly cap counts them).
 */
export function recentCounts(view: Pick<CampaignSettingsView, "recent_counts">): Record<CampaignMessageStatus, number> {
  const counts: Record<CampaignMessageStatus, number> = { sent: 0, booked: 0, skipped: 0 };
  for (const entry of view.recent_counts ?? []) {
    counts[entry.status] += entry.count;
  }
  return { ...counts, sent: counts.sent + counts.booked };
}
