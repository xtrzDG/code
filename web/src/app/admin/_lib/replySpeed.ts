import type { Schema } from "@/api/types";
import { formatNumber } from "@/lib/format";

export type ClientReplySpeed = Schema<"ClientReplySpeed">;
export type ChannelReplySpeed = Schema<"ChannelReplySpeed">;

/** The 95th percentile above which a client gets SLOW_REPLIES (the API's rule, 15 s). */
export const SLOW_REPLY_P95_MS = 15_000;

const MILLISECONDS_PER_SECOND = 1000;
const SECONDS_PER_MINUTE = 60;

/** How a wait reads: "0.8 s", "12 s", "3 min" (whole minutes from two minutes on). */
export function formatWait(milliseconds: number, locale: string): { value: string; unit: "seconds" | "minutes" } {
  const seconds = milliseconds / MILLISECONDS_PER_SECOND;
  if (seconds >= 2 * SECONDS_PER_MINUTE) {
    return { value: formatNumber(Math.round(seconds / SECONDS_PER_MINUTE), locale), unit: "minutes" };
  }
  const digits = seconds < 10 ? 1 : 0;
  return {
    value: formatNumber(seconds, locale, { minimumFractionDigits: digits, maximumFractionDigits: digits }),
    unit: "seconds",
  };
}

/** A 95th percentile the admin should look at. */
export function isSlowPercentile(milliseconds: number | null | undefined): boolean {
  return milliseconds !== null && milliseconds !== undefined && milliseconds > SLOW_REPLY_P95_MS;
}

/** The channels of a reply-speed summary, the busiest first (as the API sends them). */
export function channelRows(speed: ClientReplySpeed | undefined): ChannelReplySpeed[] {
  return [...(speed?.channels ?? [])].sort((first, second) => second.reply_count - first.reply_count);
}
