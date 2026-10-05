import { describe, expect, it } from "vitest";

import { en } from "@/i18n/messages/en";
import { createTranslator } from "@/i18n/translate";

import { timelineDetails, timelineHeadline, timelineTone, type TimelineEntry, type TimelineWords } from "./timeline";

const { t } = createTranslator("en", en);
const words: TimelineWords = {
  t,
  money: (money) => `${money.amount_minor / 100} ${money.currency_code}`,
  percent: (percent) => `${percent}%`,
  plan: (plan) => `plan:${plan}`,
  health: (status) => `health:${status}`,
  issue: (issue) => `issue:${issue}`,
  channel: (channel) => `channel:${channel}`,
  auditAction: (action) => `action:${action}`,
  auditEntity: (entity) => `entity:${entity}`,
};

function entry(fields: Partial<TimelineEntry> & Pick<TimelineEntry, "kind" | "event">): TimelineEntry {
  return { occurred_at: 1, health_issues: [], ...fields };
}

describe("timeline lines", () => {
  it("names an admin's action, its entity and the credit it granted", () => {
    const grant = entry({
      kind: "admin_action",
      event: "audit_entry",
      audit_action: "admin_credit_granted",
      audit_entity: "billing_credit",
      amount: { amount_minor: 5_000, currency_code: "GEL" },
    });
    expect(timelineHeadline(grant, words)).toBe("action:admin_credit_granted: entity:billing_credit");
    expect(timelineDetails(grant, words)).toEqual(["Credit: 50 GEL"]);
    expect(timelineTone(grant)).toBe("accent");
  });

  it("tells a bill paid by hand with its number and how the money came", () => {
    const paid = entry({
      kind: "billing",
      event: "invoice_paid",
      amount: { amount_minor: 13_500, currency_code: "GEL" },
      invoice_number: "AW-2026-0007",
      payment_method: "bank_transfer",
    });
    expect(timelineHeadline(paid, words)).toBe("Bill paid: 135 GEL");
    expect(timelineDetails(paid, words)).toEqual(["No. AW-2026-0007", "recorded as a bank transfer"]);
    expect(timelineTone(paid)).toBe("info");
  });

  it("shows a bill's discount and the monthly price of a plan change", () => {
    const issued = entry({ kind: "billing", event: "invoice_issued", amount: { amount_minor: 100, currency_code: "EUR" }, discount_percent: 20 });
    expect(timelineDetails(issued, words)).toEqual(["20% off"]);
    const changed = entry({
      kind: "billing",
      event: "plan_changed",
      plan_key: "voice_and_chat",
      previous_plan_key: "chat",
      amount: { amount_minor: 9_900, currency_code: "EUR" },
    });
    expect(timelineHeadline(changed, words)).toBe("Plan changed from plan:chat to plan:voice_and_chat");
    expect(timelineDetails(changed, words)).toEqual(["99 EUR a month"]);
  });

  it("tells a health change with its issues, toned by where it went", () => {
    const worse = entry({ kind: "health", event: "health_changed", health_from: "attention", health_to: "critical", health_issues: ["payment_past_due"] });
    expect(timelineHeadline(worse, words)).toBe("Health went from health:attention to health:critical");
    expect(timelineDetails(worse, words)).toEqual(["Issues: issue:payment_past_due"]);
    expect(timelineTone(worse)).toBe("danger");
    expect(timelineTone({ ...worse, health_to: "healthy" })).toBe("success");
  });

  it("reads a milestone without facts and a missing value as a dash", () => {
    expect(timelineHeadline(entry({ kind: "milestone", event: "went_live" }), words)).toBe("Went live");
    expect(timelineHeadline(entry({ kind: "milestone", event: "channel_connected" }), words)).toBe("Channel connected: —");
    expect(timelineDetails(entry({ kind: "milestone", event: "went_live" }), words)).toEqual([]);
  });
});
