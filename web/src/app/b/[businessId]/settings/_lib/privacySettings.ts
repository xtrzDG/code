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

/** The API's bounds (ConversationRetentionDays, LlmTurnRetentionDays). */
export const CONVERSATION_DAYS_MIN = 30;
export const CONVERSATION_DAYS_MAX = 3650;
export const MODEL_RECORD_DAYS_MAX = 30;
export const RECOMMENDED_CONVERSATION_DAYS = 730;

export const CONVERSATION_PERIODS: readonly number[] = [30, 90, 180, 365, 730, 1095, 1825];
export const MODEL_RECORD_PERIODS: readonly number[] = [7, 14, 30];

export interface RetentionForm {
  conversationDays: number;
  modelRecordDays: number;
}

export function retentionForm(view: PrivacySettingsView): RetentionForm {
  return {
    conversationDays: view.conversation_retention_days,
    modelRecordDays: view.llm_turn_retention_days,
  };
}

export function retentionBody(form: RetentionForm): PrivacySettingsBody {
  return {
    conversation_retention_days: form.conversationDays,
    llm_turn_retention_days: form.modelRecordDays,
  };
}

/** Turning the nightly quality sample of real conversations on or off: the stored periods unchanged. */
export function qualitySamplingBody(view: PrivacySettingsView, allowed: boolean): PrivacySettingsBody {
  return {
    conversation_retention_days: view.conversation_retention_days,
    llm_turn_retention_days: view.llm_turn_retention_days,
    quality_sampling_allowed: allowed,
  };
}

export function isSameRetention(form: RetentionForm, view: PrivacySettingsView): boolean {
  return (
    form.conversationDays === view.conversation_retention_days && form.modelRecordDays === view.llm_turn_retention_days
  );
}

/** A shorter period deletes data at the next cleanup: the owner confirms it first. */
export function isShorterRetention(form: RetentionForm, view: PrivacySettingsView): boolean {
  return form.conversationDays < view.conversation_retention_days || form.modelRecordDays < view.llm_turn_retention_days;
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
