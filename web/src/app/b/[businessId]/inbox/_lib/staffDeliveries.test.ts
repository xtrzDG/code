import { describe, expect, it } from "vitest";

import type { MessageView } from "@/components/insights/types";

import { describeDelivery, isTemplateRejected, latestDeliveredReply } from "./staffDeliveries";

function message(id: string, author: MessageView["author"], delivery: MessageView["delivery"] = null): MessageView {
  return {
    id,
    author,
    delivery,
    direction: author === "customer" ? "inbound" : "outbound",
    text: id,
    created_at: 1_790_856_000_000_000,
    cost_micro_usd: 0,
  } as MessageView;
}

const rejected: MessageView["delivery"] = { state: "failed", failure_reason: "template_rejected", attempts: 1 };
const delivered: MessageView["delivery"] = { state: "delivered", attempts: 1, delivered_at: 1_790_856_000_000_000 };

describe("staff reply deliveries", () => {
  it("finds the newest staff reply that went through a messenger", () => {
    const messages = [message("a", "staff", delivered), message("b", "customer"), message("c", "staff")];

    expect(latestDeliveredReply(messages)?.id).toBe("a");
    expect(latestDeliveredReply([message("d", "assistant")])).toBeNull();
  });

  it("tells a refused template only while it is the newest reply's outcome", () => {
    expect(isTemplateRejected([message("a", "staff", rejected)])).toBe(true);
    expect(isTemplateRejected([message("a", "staff", rejected), message("b", "staff", delivered)])).toBe(false);
    expect(
      isTemplateRejected([message("a", "staff", { state: "failed", failure_reason: "recipient_refused", attempts: 1 })]),
    ).toBe(false);
    expect(isTemplateRejected([])).toBe(false);
  });
});

describe("the delivery chip", () => {
  it("says why a reply waits for another try, and when", () => {
    expect(
      describeDelivery({ state: "retrying", failure_reason: "provider_unavailable", attempts: 2, next_attempt_at: 42 }),
    ).toEqual({
      state: "messageDelivery.states.retrying",
      reason: "messageDelivery.reasons.provider_unavailable",
      nextAttemptAt: 42,
    });
  });

  it("says why a reply was given up, and nothing more once it arrived", () => {
    expect(describeDelivery({ state: "failed", failure_reason: "expired", attempts: 0 })).toEqual({
      state: "messageDelivery.states.failed",
      reason: "messageDelivery.reasons.expired",
      nextAttemptAt: null,
    });
    expect(describeDelivery({ state: "delivered", failure_reason: "rate_limited", attempts: 3 })).toEqual({
      state: "messageDelivery.states.delivered",
      reason: null,
      nextAttemptAt: null,
    });
    expect(describeDelivery({ state: "sending", attempts: 0 }).reason).toBeNull();
  });
});
