/**
 * Settings → Privacy → "How long data is kept": the periods an owner
 * picks from, how each reads ("2 years (recommended)"), whether a change
 * shortens a period (it deletes data at the next cleanup), and what the
 * latest cleanup removed.
 */

import type { RequestBody, Schema } from "@/api/types";

export type PrivacySettingsView = Schema<"PrivacySettingsView">;
export type PrivacySettingsBody = RequestBody<"/v1/businesses/{business_id}/privacy-settings", "put">;
export type RetentionPurgeCounts = Schema<"RetentionPurgeCounts">;
export type SubProcessor = Schema<"SubProcessor">;

export const MODEL_RECORD_DAYS_MAX = 30;
export const RECOMMENDED_CONVERSATION_DAYS = 730;

export const CONVERSATION_PERIODS: readonly number[] = [30, 90, 180, 365, 730, 1095, 1825];
export const MODEL_RECORD_PERIODS: readonly number[] = [7, 14, 30];

export interface RetentionForm {
  conversationDays: number;
  modelRecordDays: number;
  /** Whether the nightly quality sample may read a few real conversations. */
  isQualitySamplingAllowed: boolean;
}

export function retentionForm(view: PrivacySettingsView): RetentionForm {
  return {
    conversationDays: view.conversation_retention_days,
    modelRecordDays: view.llm_turn_retention_days,
    isQualitySamplingAllowed: view.quality_sampling_allowed,
  };
}

export function retentionBody(form: RetentionForm): PrivacySettingsBody {
  return {
    conversation_retention_days: form.conversationDays,
    llm_turn_retention_days: form.modelRecordDays,
    quality_sampling_allowed: form.isQualitySamplingAllowed,
  };
}

export function isSameRetention(form: RetentionForm, view: PrivacySettingsView): boolean {
  return (
    form.conversationDays === view.conversation_retention_days &&
    form.modelRecordDays === view.llm_turn_retention_days &&
    form.isQualitySamplingAllowed === view.quality_sampling_allowed
  );
}

/** The periods made shorter: they delete data at the next cleanup, so the owner confirms them first. */
export function shorterPeriods(form: RetentionForm, view: PrivacySettingsView): ("conversationDays" | "modelRecordDays")[] {
  return [
    ...(form.conversationDays < view.conversation_retention_days ? (["conversationDays"] as const) : []),
    ...(form.modelRecordDays < view.llm_turn_retention_days ? (["modelRecordDays"] as const) : []),
  ];
}

/** The choices of a select: the presets and the stored value (set some other way) in order. */
export function periodChoices(presets: readonly number[], current: number): number[] {
  return [...new Set([...presets, current])].sort((first, second) => first - second);
}

/** The kinds of records a cleanup counts, in the order the card names them. */
export const PURGE_COUNT_FIELDS = [
  "deleted_messages",
  "deleted_llm_turns",
  "deleted_notes",
  "deleted_media",
  "deleted_missed_calls",
  "erased_calls",
  "anonymized_leads",
  "anonymized_bookings",
  "anonymized_handoffs",
] as const satisfies readonly (keyof RetentionPurgeCounts)[];

export type PurgeCountField = (typeof PURGE_COUNT_FIELDS)[number];

/** The kinds a cleanup removed (count above zero) and the total. */
export function purgeSummary(counts: RetentionPurgeCounts): {
  total: number;
  parts: { field: PurgeCountField; count: number }[];
} {
  const parts = PURGE_COUNT_FIELDS.map((field) => ({ field, count: counts[field] ?? 0 })).filter(
    (part) => part.count > 0,
  );
  return { total: parts.reduce((sum, part) => sum + part.count, 0), parts };
}

/** The sub-processors that delete copies (the card names them), in a stable order. */
export const NAMED_PROCESSORS = ["langfuse", "elevenlabs"] as const satisfies readonly SubProcessor[];
