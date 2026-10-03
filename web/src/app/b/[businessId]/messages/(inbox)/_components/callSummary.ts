/**
 * The summary of a call to show on its card: the one written in the
 * reader's language, else in its base language, else the first one (the
 * owner's language).
 */

import type { CallView } from "@/components/insights/types";

export type CallSummary = NonNullable<CallView["summaries"]>[number];

export function pickCallSummary(call: CallView, locale: string): CallSummary | null {
  const summaries = call.summaries ?? [];
  const base = (tag: string) => tag.split("-")[0]?.toLowerCase();
  return (
    summaries.find((summary) => summary.language === locale) ??
    summaries.find((summary) => base(summary.language) === base(locale)) ??
    summaries[0] ??
    null
  );
}
