import { describe, expect, it } from "vitest";

import { actorLabel, auditQuery, EMPTY_AUDIT_FILTERS, hasAuditFilters, nextDay } from "./audit";
import { member } from "./settingsFixtures";

describe("audit log", () => {
  it("names actors who are team members", () => {
    const members = [member({ user_id: "u1", display_name: "Nino" })];
    expect(actorLabel("u1", members)).toBe("Nino");
    expect(actorLabel("u9", members)).toBeNull();
    expect(actorLabel(null, members)).toBeNull();
  });

  it("turns the filters into the API query", () => {
    const dayStart = (day: string) => Date.parse(`${day}T00:00:00Z`) * 1000;
    expect(auditQuery(EMPTY_AUDIT_FILTERS, dayStart)).toEqual({});
    expect(hasAuditFilters(EMPTY_AUDIT_FILTERS)).toBe(false);
    const filters = { action: "export" as const, entity: "contact", actorId: "u1", from: "2026-09-30", to: "2026-09-30" };
    expect(hasAuditFilters(filters)).toBe(true);
    expect(auditQuery(filters, dayStart)).toEqual({
      action: "export",
      entity: "contact",
      actor_id: "u1",
      since: String(Date.UTC(2026, 8, 30) * 1000),
      until: String(Date.UTC(2026, 9, 1) * 1000),
    });
  });

  it("counts the next calendar day across months and years", () => {
    expect(nextDay("2026-02-28")).toBe("2026-03-01");
    expect(nextDay("2028-02-28")).toBe("2028-02-29");
    expect(nextDay("2026-12-31")).toBe("2027-01-01");
  });
});
