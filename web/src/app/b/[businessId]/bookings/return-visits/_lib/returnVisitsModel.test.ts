import { describe, expect, it } from "vitest";

import {
  campaignBody,
  campaignErrors,
  campaignForm,
  daysLabel,
  hasErrors,
  isSameCampaign,
  recentCounts,
  suggestionKey,
  wholeNumber,
  type CampaignSettingsView,
} from "./returnVisitsModel";

const STORED: CampaignSettingsView = {
  is_enabled: false,
  rule_kind: "rebook",
  delay_days: 35,
  audience: "all_customers",
  segment_id: null,
  segment_name: null,
  monthly_cap: 100,
  niche_rule_kind: "rebook",
  niche_delay_days: 35,
  month_sent_count: 3,
  recent_counts: [
    { status: "sent", count: 4 },
    { status: "booked", count: 2 },
  ],
  previews: [{ language: "en", text: "We would love to see you again." }],
};

describe("the return-visit form", () => {
  it("starts from what is stored and has nothing to save", () => {
    const form = campaignForm(STORED);
    expect(form).toEqual({
      isEnabled: false,
      ruleKind: "rebook",
      delayDays: "35",
      audience: "all_customers",
      segmentId: "",
      monthlyCap: "100",
    });
    expect(isSameCampaign(form, STORED)).toBe(true);
    expect(isSameCampaign({ ...form, isEnabled: true }, STORED)).toBe(false);
    expect(isSameCampaign({ ...form, delayDays: " 35 " }, STORED)).toBe(true);
  });

  it("checks the days, the cap and the segment", () => {
    const form = campaignForm(STORED);
    expect(hasErrors(campaignErrors(form))).toBe(false);
    expect(campaignErrors({ ...form, delayDays: "0" }).delayDays).toBe("returnVisits.settings.errors.days");
    expect(campaignErrors({ ...form, delayDays: "731" }).delayDays).not.toBeNull();
    expect(campaignErrors({ ...form, delayDays: "2.5" }).delayDays).not.toBeNull();
    expect(campaignErrors({ ...form, monthlyCap: "2001" }).monthlyCap).toBe("returnVisits.settings.errors.cap");
    expect(campaignErrors({ ...form, audience: "segment" }).segment).toBe("returnVisits.settings.errors.segment");
    expect(campaignErrors({ ...form, audience: "segment", segmentId: "segment_1" }).segment).toBeNull();
  });

  it("sends a segment only for a segment audience", () => {
    const form = { ...campaignForm(STORED), isEnabled: true, segmentId: "segment_1", delayDays: "42" };
    expect(campaignBody(form)).toEqual({
      is_enabled: true,
      rule_kind: "rebook",
      delay_days: 42,
      audience: "all_customers",
      segment_id: null,
      monthly_cap: 100,
    });
    expect(campaignBody({ ...form, audience: "segment" }).segment_id).toBe("segment_1");
  });

  it("reads whole numbers within bounds only", () => {
    expect(wholeNumber("12", { min: 1, max: 20 })).toBe(12);
    expect(wholeNumber("-1", { min: 1, max: 20 })).toBeNull();
    expect(wholeNumber("", { min: 1, max: 20 })).toBeNull();
  });

  it("counts days before arrival for the pre-arrival note, after the last visit otherwise", () => {
    expect(daysLabel("pre_arrival")).toBe("returnVisits.settings.daysBefore");
    expect(daysLabel("recall")).toBe("returnVisits.settings.daysAfter");
    expect(suggestionKey("pre_arrival")).toBe("returnVisits.settings.suggestedBefore");
    expect(suggestionKey("rebook")).toBe("returnVisits.settings.suggested");
  });

  it("fills every status of the last 30 days", () => {
    expect(recentCounts(STORED)).toEqual({ sent: 4, booked: 2, skipped: 0 });
  });
});
