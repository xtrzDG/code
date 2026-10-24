/**
 * What the delivery of the staff replies in a transcript means for the
 * reply box: a WhatsApp template Meta refused stays refused until the
 * owner fixes it, so the box says so instead of offering another try.
 */

import type { MessageView } from "@/components/insights/types";
import type { MessageKey } from "@/i18n/translate";

export type MessageDelivery = NonNullable<MessageView["delivery"]>;

/** The failure reason of a WhatsApp template Meta did not accept. */
const TEMPLATE_REJECTED = "template_rejected";

/** The newest staff reply sent through a messenger, if any. */
export function latestDeliveredReply(messages: readonly MessageView[]): MessageView | null {
  return messages.findLast((message) => message.author === "staff" && Boolean(message.delivery)) ?? null;
}

/** True when the newest staff reply failed because Meta refused its template. */
export function isTemplateRejected(messages: readonly MessageView[]): boolean {
  const delivery = latestDeliveredReply(messages)?.delivery;
  return delivery?.state === "failed" && delivery.failure_reason === TEMPLATE_REJECTED;
}

/**
 * What the chip under a staff reply says: its state, why the last attempt
 * failed (while it is tried again and once it was given up) and, while it
 * waits for another try, when that is.
 */
export function describeDelivery(delivery: MessageDelivery): {
  state: MessageKey;
  reason: MessageKey | null;
  nextAttemptAt: number | null;
} {
  const isDelivered = delivery.state === "delivered";
  return {
    state: `messageDelivery.states.${delivery.state}`,
    reason: !isDelivered && delivery.failure_reason ? `messageDelivery.reasons.${delivery.failure_reason}` : null,
    nextAttemptAt: delivery.state === "retrying" ? (delivery.next_attempt_at ?? null) : null,
  };
}
