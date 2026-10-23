import { describe, expect, it } from "vitest";

import type { ApiErrorReason } from "@/api/errors";
import type { BusinessClosureView, UserMembershipView } from "@/api/types";

import { closureCountdown, daysUntilDeletion, refusedNames } from "./closure";

const DAY_MS = 24 * 60 * 60 * 1000;
const NOW_MS = Date.UTC(2026, 9, 23, 12, 0);
const micros = (ms: number) => ms * 1000;

const closing: BusinessClosureView = {
  business_id: "business_1",
  state: "pending_deletion",
  reason: "owner_request",
  requested_at: micros(NOW_MS - 2 * DAY_MS),
  delete_after: micros(NOW_MS + 28 * DAY_MS),
  actor_name: "Nino",
  can_cancel: true,
  viewer_is_owner: true,
};

function membership(businessId: string, name: string, brand?: [string, string]): UserMembershipView {
  return {
    business_id: businessId,
    business_name: name,
    business_status: "live",
    country_code: "GE",
    role: "owner",
    brand_id: brand?.[0] ?? null,
    brand_name: brand?.[1] ?? null,
  };
}

describe("the countdown of a closing business", () => {
  it("counts whole days up, and nothing once the deletion is due", () => {
    expect(daysUntilDeletion(micros(NOW_MS + 28 * DAY_MS), NOW_MS)).toBe(28);
    expect(daysUntilDeletion(micros(NOW_MS + DAY_MS / 3), NOW_MS)).toBe(1);
    expect(daysUntilDeletion(micros(NOW_MS - 1), NOW_MS)).toBe(0);
  });

  it("is there only while the business is closing", () => {
    expect(closureCountdown(closing, NOW_MS)).toEqual({
      deleteAfter: closing.delete_after,
      requestedAt: closing.requested_at,
      daysLeft: 28,
      isUnpaid: false,
      canCancel: true,
      actorName: "Nino",
    });
    expect(closureCountdown({ business_id: "business_1", state: "active" }, NOW_MS)).toBeNull();
    expect(closureCountdown({ ...closing, state: "deleting" }, NOW_MS)).toBeNull();
    expect(closureCountdown(undefined, NOW_MS)).toBeNull();
  });

  it("knows a closure for non-payment that cannot be cancelled before paying", () => {
    const unpaid = closureCountdown({ ...closing, reason: "unpaid_subscription", actor_name: null, can_cancel: false }, NOW_MS);

    expect(unpaid).toMatchObject({ isUnpaid: true, canCancel: false, actorName: null });
  });
});

describe("the names a refused account deletion is about", () => {
  const memberships = [
    membership("business_1", "Café Tbilisi"),
    membership("business_2", "Salobie", ["brand_1", "Mtsvane"]),
    membership("business_3", "Mtsvane Vake", ["brand_1", "Mtsvane"]),
  ];
  const reason = (code: string, details: string[]): ApiErrorReason => ({ code, message: "", details });

  it("names the businesses by their memberships, leaving out ids it does not know", () => {
    expect(refusedNames(reason("last_business_owner", ["business_2", "business_9", "business_1"]), memberships)).toEqual([
      "Salobie",
      "Café Tbilisi",
    ]);
  });

  it("names a brand once, by the name its locations carry", () => {
    expect(refusedNames(reason("last_brand_owner", ["brand_1"]), memberships)).toEqual(["Mtsvane"]);
  });
});
