import { describe, expect, it } from "vitest";

import { en } from "@/i18n/messages/en";
import { ka } from "@/i18n/messages/ka";
import { ru } from "@/i18n/messages/ru";

import { channelHealth, channelProblem, problemFix, type ChannelProblem, type DeliveryFailureReason } from "./channelHealth";
import type { ChannelView } from "./channels";

const channel = (overrides: Partial<ChannelView>): ChannelView => ({
  id: "channel_1",
  business_id: "business_1",
  channel: "telegram",
  status: "connected",
  has_credential: true,
  updated_at: 1,
  ...overrides,
});

const REASONS: readonly DeliveryFailureReason[] = [
  "rate_limited",
  "provider_unavailable",
  "recipient_refused",
  "template_rejected",
  "channel_disconnected",
  "credential_rejected",
  "not_configured",
  "expired",
];

describe("a channel's health", () => {
  it("shows when the last message came in and the last reply went out", () => {
    const health = channelHealth("telegram", channel({ last_inbound_at: 100, last_outbound_at: 200 }));

    expect(health?.activity).toEqual({ lastInboundAt: 100, lastOutboundAt: 200 });
    expect(health?.problem).toBeNull();
    expect(channelHealth("telegram", channel({}))?.activity).toEqual({ lastInboundAt: null, lastOutboundAt: null });
  });

  it("says nothing for a channel that is off, and no message times for calls", () => {
    expect(channelHealth("telegram", undefined)).toBeNull();
    expect(channelHealth("telegram", channel({ status: "disabled" }))).toBeNull();
    expect(channelHealth("phone", channel({ channel: "phone" }))?.activity).toBeNull();
    expect(channelHealth("telegram", channel({ status: "pending" }))?.activity).toBeNull();
  });

  it("names the problem by the API's reason, an older error without one, or a missing public address", () => {
    expect(channelProblem(channel({ status: "error", last_error_reason: "credential_rejected" }))).toBe("credential_rejected");
    expect(channelProblem(channel({ status: "error", last_error: "Unauthorized" }))).toBe("unknown");
    expect(channelProblem(channel({ last_error_reason: "recipient_refused" }))).toBe("recipient_refused");
    expect(channelProblem(channel({ channel: "whatsapp", link_state: "missing_public_address" }))).toBe(
      "missing_public_address",
    );
    expect(channelProblem(channel({}))).toBeNull();
  });

  it("offers the fix that helps: connect again for a refused key, templates for a refused template", () => {
    expect(problemFix("telegram", "credential_rejected")).toBe("reconnect");
    expect(problemFix("whatsapp", "missing_public_address")).toBe("reconnect");
    expect(problemFix("telegram", "unknown")).toBe("reconnect");
    expect(problemFix("whatsapp", "template_rejected")).toBe("templates");
    expect(problemFix("telegram", "template_rejected")).toBeNull();
    // Passing troubles and the customer's side need nothing from the owner.
    for (const reason of ["rate_limited", "provider_unavailable", "recipient_refused", "expired"] as const) {
      expect(problemFix("telegram", reason)).toBeNull();
    }
  });

  it("is loud for a stopped channel and quiet for a passing trouble", () => {
    expect(channelHealth("telegram", channel({ status: "error", last_error_reason: "credential_rejected", last_error_at: 5 })))
      .toMatchObject({ tone: "danger", fix: "reconnect", since: 5 });
    expect(channelHealth("telegram", channel({ last_error_reason: "recipient_refused", last_error_at: 5 }))).toMatchObject({
      tone: "info",
      fix: null,
    });
    expect(channelHealth("whatsapp", channel({ channel: "whatsapp", link_state: "missing_public_address" }))).toMatchObject({
      tone: "warning",
      fix: "reconnect",
      since: null,
    });
  });

  it("has a plain-word text for every problem in every language, naming no internals", () => {
    const problems: ChannelProblem[] = [...REASONS, "unknown", "missing_public_address"];
    for (const messages of [en, ru, ka]) {
      for (const problem of problems) {
        const text = messages.channelSetup.health.problems[problem];
        expect(text, problem).toBeTruthy();
        expect(text, problem).not.toMatch(/token|webhook|api|credential|_/i);
      }
    }
  });
});
