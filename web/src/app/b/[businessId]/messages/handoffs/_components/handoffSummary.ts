/**
 * What a handoff card says happened. A handoff the platform created carries
 * a `summary_code`, rendered from the dictionary in the reader's language
 * with the flagged values (as written, comma-separated like the staff
 * notifications) and the quoted words; the model's own summary
 * (written in the staff language) is shown as it is.
 */

import type { HandoffListItem } from "@/components/insights/types";
import type { MessageKey, Translator } from "@/i18n/translate";

type SummaryCode = NonNullable<HandoffListItem["summary_code"]>;
type SummarySource = Pick<HandoffListItem, "summary" | "summary_code" | "quoted_text" | "flagged_values">;

export interface HandoffSummaryView {
  text: string;
  quote: { label: string; text: string } | null;
}

const SUMMARY_TEXTS: Record<SummaryCode, MessageKey> = {
  model_declined: "handoffs.summaryCodes.model_declined",
  model_unavailable: "handoffs.summaryCodes.model_unavailable",
  answer_unfinished: "handoffs.summaryCodes.answer_unfinished",
  unverified_values: "handoffs.summaryCodes.unverified_values",
  call_booking_unverified_values: "handoffs.summaryCodes.call_booking_unverified_values",
  call_request_unverified_values: "handoffs.summaryCodes.call_request_unverified_values",
  reply_undelivered: "handoffs.summaryCodes.reply_undelivered",
  data_erased: "handoffs.summaryCodes.data_erased",
};

const SUMMARY_TEXTS_WITH_VALUES: Partial<Record<SummaryCode, MessageKey>> = {
  unverified_values: "handoffs.summaryCodesWithValues.unverified_values",
  call_booking_unverified_values: "handoffs.summaryCodesWithValues.call_booking_unverified_values",
  call_request_unverified_values: "handoffs.summaryCodesWithValues.call_request_unverified_values",
};

export function handoffSummary(handoff: SummarySource, t: Translator["t"]): HandoffSummaryView {
  const code = handoff.summary_code;
  if (!code) {
    return { text: handoff.summary, quote: null };
  }

  const values = handoff.flagged_values ?? [];
  const withValues = SUMMARY_TEXTS_WITH_VALUES[code];
  const text =
    values.length > 0 && withValues ? t(withValues, { values: values.join(", ") }) : t(SUMMARY_TEXTS[code]);
  const quoted = handoff.quoted_text;
  return {
    text,
    quote: quoted
      ? { label: t(code === "reply_undelivered" ? "handoffs.quote.reply" : "handoffs.quote.customer"), text: quoted }
      : null,
  };
}
