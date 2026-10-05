import { describe, expect, it } from "vitest";

import { formatDate } from "./format";
import { calendarDayMoment, dpaReacceptance, type DpaStatus } from "./dpaNotice";

function status(overrides: Partial<DpaStatus> = {}): DpaStatus {
  return {
    business_id: "business_1",
    current_document_version: "2026-10-06",
    is_current_version_accepted: false,
    needs_reacceptance: true,
    acceptance_due_on: "2026-11-05",
    document_url: "/v1/legal/dpa/2026-10-06",
    latest_acceptance: null,
    ...overrides,
  };
}

describe("dpaReacceptance", () => {
  it("asks an owner who accepted an earlier version, with the day it is due", () => {
    expect(dpaReacceptance(status(), "2026-10-07")).toEqual({
      version: "2026-10-06",
      dueOn: "2026-11-05",
      isOverdue: false,
    });
    expect(dpaReacceptance(status(), "2026-11-05")?.isOverdue).toBe(false);
    expect(dpaReacceptance(status(), "2026-11-06")?.isOverdue).toBe(true);
  });

  it("says nothing once accepted, before any acceptance, or while loading", () => {
    expect(dpaReacceptance(status({ is_current_version_accepted: true }), "2026-10-07")).toBeNull();
    expect(dpaReacceptance(status({ needs_reacceptance: false, acceptance_due_on: null }), "2026-10-07")).toBeNull();
    expect(dpaReacceptance(status({ acceptance_due_on: null }), "2026-10-07")).toBeNull();
    expect(dpaReacceptance(undefined, "2026-10-07")).toBeNull();
  });
});

describe("calendarDayMoment", () => {
  it("reads as the same day wherever it is formatted in UTC", () => {
    expect(formatDate(calendarDayMoment("2026-11-05"), { locale: "en", timeZone: "UTC" })).toBe("Nov 5, 2026");
  });
});
