/**
 * Settings → Calls: the owner's form (summaries, text-backs, the WhatsApp
 * template name, the SMS fallback), what a caller who did not get through
 * would get with it, and the labels of the latest text-backs.
 */

import type { RequestBody, Schema } from "@/api/types";
import type { BadgeTone } from "@/components/ui";
import type { MessageKey } from "@/i18n/translate";

export type CallSettingsView = Schema<"CallSettingsView">;
export type CallSettingsBody = RequestBody<"/v1/businesses/{business_id}/call-settings", "put">;
export type TextBackView = Schema<"TextBackView">;
export type TextBackPage = Schema<"TextBackPage">;
export type TextBackStatus = Schema<"TextBackStatus">;
export type TextBackChannel = Schema<"TextBackChannel">;
export type MissedCallReason = Schema<"MissedCallReason">;
export type TextBackSkipReason = Schema<"TextBackSkipReason">;

/** Settings → Calls lists the latest text-backs only (the API pages further). */
export const TEXT_BACK_LIST_SIZE = 20;

/** What Meta accepts as a template name (the API checks the same). */
const TEMPLATE_NAME_PATTERN = /^[a-z0-9_]{1,512}$/;

export interface CallSettingsForm {
  isSummaryEnabled: boolean;
  isTextBackEnabled: boolean;
  /** As typed; an empty name means "no WhatsApp template". */
  templateName: string;
  isSmsFallbackEnabled: boolean;
}

export function callSettingsForm(view: CallSettingsView): CallSettingsForm {
  return {
    isSummaryEnabled: view.is_summary_enabled,
    isTextBackEnabled: view.is_text_back_enabled,
    templateName: view.text_back_template_name ?? "",
    isSmsFallbackEnabled: view.is_sms_fallback_enabled,
  };
}

export function callSettingsBody(form: CallSettingsForm): CallSettingsBody {
  const templateName = form.templateName.trim();
  return {
    is_summary_enabled: form.isSummaryEnabled,
    is_text_back_enabled: form.isTextBackEnabled,
    text_back_template_name: templateName === "" ? null : templateName,
    is_sms_fallback_enabled: form.isSmsFallbackEnabled,
  };
}

/** The error under the template name, or null when it can be saved. */
export function templateNameError(form: CallSettingsForm): MessageKey | null {
  const templateName = form.templateName.trim();
  if (templateName === "" || TEMPLATE_NAME_PATTERN.test(templateName)) {
    return null;
  }
  return "callSettings.textBack.templateInvalid";
}

export function isSameCallSettings(form: CallSettingsForm, view: CallSettingsView): boolean {
  const body = callSettingsBody(form);
  return (
    body.is_summary_enabled === view.is_summary_enabled &&
    body.is_text_back_enabled === view.is_text_back_enabled &&
    (body.text_back_template_name ?? null) === (view.text_back_template_name ?? null) &&
    body.is_sms_fallback_enabled === view.is_sms_fallback_enabled
  );
}

export type TextBackReadiness = "off" | "whatsapp" | "sms" | "none";

/**
 * What a caller who did not get through gets with these choices: the
 * WhatsApp template (a connected number and a template name), else an SMS
 * (allowed and set up on the platform), else nothing.
 */
export function textBackReadiness(form: CallSettingsForm, view: CallSettingsView): TextBackReadiness {
  if (!form.isTextBackEnabled) {
    return "off";
  }
  if (view.is_whatsapp_connected && form.templateName.trim() !== "") {
    return "whatsapp";
  }
  if (form.isSmsFallbackEnabled && view.is_sms_available) {
    return "sms";
  }
  return "none";
}

export const READINESS_TEXTS: Record<TextBackReadiness, MessageKey> = {
  off: "callSettings.textBack.readiness.off",
  whatsapp: "callSettings.textBack.readiness.whatsapp",
  sms: "callSettings.textBack.readiness.sms",
  none: "callSettings.textBack.readiness.none",
};

export const READINESS_TONES: Record<TextBackReadiness, "info" | "success" | "warning"> = {
  off: "info",
  whatsapp: "success",
  sms: "success",
  none: "warning",
};

export const TEXT_BACK_STATUS_LABELS: Record<TextBackStatus, MessageKey> = {
  queued: "callSettings.history.statuses.queued",
  sent: "callSettings.history.statuses.sent",
  failed: "callSettings.history.statuses.failed",
  skipped: "callSettings.history.statuses.skipped",
};

export const TEXT_BACK_STATUS_TONES: Record<TextBackStatus, BadgeTone> = {
  queued: "info",
  sent: "success",
  failed: "danger",
  skipped: "neutral",
};

export const TEXT_BACK_CHANNEL_LABELS: Record<TextBackChannel, MessageKey> = {
  whatsapp: "callSettings.history.channels.whatsapp",
  sms: "callSettings.history.channels.sms",
};

export const MISSED_CALL_REASON_LABELS: Record<MissedCallReason, MessageKey> = {
  no_answer: "callSettings.history.reasons.no_answer",
  busy: "callSettings.history.reasons.busy",
  abandoned: "callSettings.history.reasons.abandoned",
  line_failed: "callSettings.history.reasons.line_failed",
  not_started: "callSettings.history.reasons.not_started",
  no_speech: "callSettings.history.reasons.no_speech",
  transfer_unanswered: "callSettings.history.reasons.transfer_unanswered",
};

export const SKIP_REASON_LABELS: Record<TextBackSkipReason, MessageKey> = {
  turned_off: "callSettings.history.skipReasons.turned_off",
  opted_out: "callSettings.history.skipReasons.opted_out",
  already_texted: "callSettings.history.skipReasons.already_texted",
  daily_limit: "callSettings.history.skipReasons.daily_limit",
  in_conversation: "callSettings.history.skipReasons.in_conversation",
  no_channel: "callSettings.history.skipReasons.no_channel",
  not_live: "callSettings.history.skipReasons.not_live",
  no_caller_number: "callSettings.history.skipReasons.no_caller_number",
  too_late: "callSettings.history.skipReasons.too_late",
};
