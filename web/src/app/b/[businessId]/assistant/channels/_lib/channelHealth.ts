/**
 * How a connected channel is doing, in words an owner can act on: when the
 * last customer message came in and the last reply went out, and the
 * current problem (the API's `last_error_reason`, the same reasons a failed
 * message shows) with the one thing that fixes it.
 */

import type { Schema } from "@/api/types";

import { isChannelOn, isLinkMissing, type ChannelView, type ConnectableChannel } from "./channels";

export type DeliveryFailureReason = Schema<"DeliveryFailureReason">;

/** A failure reason, a channel customers cannot be linked to, or an older error without a reason. */
export type ChannelProblem = DeliveryFailureReason | "missing_public_address" | "unknown";

/** What fixes it: connecting again (new details), or the WhatsApp templates. */
export type ChannelFix = "reconnect" | "templates";

/** How loud a problem is: it stops the channel, it needs a look, or it passes by itself. */
export type ProblemTone = "danger" | "warning" | "info";

export interface ChannelHealth {
  /** Times of the last message each way (microseconds), when the channel shows them. */
  activity: { lastInboundAt: number | null; lastOutboundAt: number | null } | null;
  problem: ChannelProblem | null;
  tone: ProblemTone;
  fix: ChannelFix | null;
  /** Since when the problem lasts (microseconds), when known. */
  since: number | null;
}

/** The platform's failures that pass by themselves (we try again) or are on the customer's side. */
const PASSING_PROBLEMS: ReadonlySet<ChannelProblem> = new Set<ChannelProblem>([
  "rate_limited",
  "provider_unavailable",
  "recipient_refused",
  "expired",
]);

const RECONNECT_PROBLEMS: ReadonlySet<ChannelProblem> = new Set<ChannelProblem>([
  "credential_rejected",
  "channel_disconnected",
  "not_configured",
  "missing_public_address",
  "unknown",
]);

/** The channel's problem now, if any: a reason the API gave, an error without one, or a missing link. */
export function channelProblem(channel: ChannelView): ChannelProblem | null {
  if (channel.last_error_reason) {
    return channel.last_error_reason;
  }
  if (channel.status === "error") {
    return "unknown";
  }
  return isLinkMissing(channel) ? "missing_public_address" : null;
}

export function problemFix(kind: ConnectableChannel, problem: ChannelProblem): ChannelFix | null {
  if (problem === "template_rejected") {
    return kind === "whatsapp" ? "templates" : null;
  }
  return RECONNECT_PROBLEMS.has(problem) ? "reconnect" : null;
}

export function problemTone(channel: ChannelView, problem: ChannelProblem): ProblemTone {
  if (PASSING_PROBLEMS.has(problem)) {
    return channel.status === "error" ? "warning" : "info";
  }
  return channel.status === "error" ? "danger" : "warning";
}

/**
 * The health of a channel that is on; null for a channel never connected
 * or switched off. Calls are not messages: the phone shows no message times.
 */
export function channelHealth(kind: ConnectableChannel, channel: ChannelView | undefined): ChannelHealth | null {
  if (!channel || !isChannelOn(channel)) {
    return null;
  }
  const problem = channelProblem(channel);
  return {
    activity:
      kind === "phone" || channel.status === "pending"
        ? null
        : { lastInboundAt: channel.last_inbound_at ?? null, lastOutboundAt: channel.last_outbound_at ?? null },
    problem,
    tone: problem ? problemTone(channel, problem) : "info",
    fix: problem ? problemFix(kind, problem) : null,
    since: problem && problem !== "missing_public_address" ? (channel.last_error_at ?? null) : null,
  };
}
