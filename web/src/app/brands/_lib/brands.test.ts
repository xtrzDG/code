import { describe, expect, it } from "vitest";

import type { UserMembershipView } from "@/api/types";

import {
  brandTotals,
  buildBrandInvite,
  groupMemberships,
  ownedFreeBusinesses,
  parsePriceMinor,
  topSources,
  type BrandLocationDashboard,
  type InviteForm,
} from "./brands";

function membership(id: string, extra: Partial<UserMembershipView> = {}): UserMembershipView {
  return {
    business_id: id,
    business_name: `Business ${id}`,
    role: "owner",
    business_status: "live",
    country_code: "GE",
    brand_id: null,
    brand_name: null,
    ...extra,
  };
}

describe("memberships grouped by brand", () => {
  it("keeps the old single list when nobody is in a brand", () => {
    const groups = groupMemberships([membership("a"), membership("b")]);

    expect(groups).toHaveLength(1);
    expect(groups[0]?.brand).toBeNull();
    expect(groups[0]?.memberships.map((item) => item.business_id)).toEqual(["a", "b"]);
  });

  it("puts each brand's locations together and the rest last", () => {
    const groups = groupMemberships([
      membership("a", { brand_id: "brand_1", brand_name: "Mtsvane Ezo" }),
      membership("b"),
      membership("c", { brand_id: "brand_1", brand_name: "Mtsvane Ezo" }),
    ]);

    expect(groups.map((group) => group.brand?.name ?? null)).toEqual(["Mtsvane Ezo", null]);
    expect(groups[0]?.memberships.map((item) => item.business_id)).toEqual(["a", "c"]);
  });

  it("keeps a location of a brand the person is not on the team of with the others", () => {
    const groups = groupMemberships([
      membership("a", { brand_id: "brand_1", brand_name: "Mtsvane Ezo" }),
      membership("b", { brand_id: "brand_2", brand_name: null }),
    ]);

    expect(groups.map((group) => group.brand?.name ?? null)).toEqual(["Mtsvane Ezo", null]);
    expect(groups[1]?.memberships.map((item) => item.business_id)).toEqual(["b"]);
    expect(ownedFreeBusinesses([membership("b", { brand_id: "brand_2", brand_name: null })])).toEqual([]);
  });

  it("offers only owned businesses outside any brand to a new brand", () => {
    const free = ownedFreeBusinesses([
      membership("a"),
      membership("b", { role: "staff" }),
      membership("c", { brand_id: "brand_1", brand_name: "X" }),
    ]);

    expect(free.map((item) => item.business_id)).toEqual(["a"]);
  });
});

function row(extra: Partial<BrandLocationDashboard> & { currency?: string; revenue?: number | null }): BrandLocationDashboard {
  const { currency = "GEL", revenue = 0, ...rest } = extra;
  return {
    location: { business_id: "x", name: "X", status: "live", niche_key: "restaurant", plan_key: "chat", country_code: "GE", currency_code: currency },
    is_locked: false,
    value: {
      currency_code: currency,
      current: { conversation_count: 3, assistant_booking_count: 2, estimated_revenue_minor: revenue },
    } as BrandLocationDashboard["value"],
    inbox: { needs_person: 1, requests: 2 } as BrandLocationDashboard["inbox"],
    ...rest,
  } as BrandLocationDashboard;
}

describe("brand totals", () => {
  it("adds up reached locations and leaves locked ones out", () => {
    const totals = brandTotals([row({ revenue: 1000 }), row({ revenue: 500 }), row({ is_locked: true, value: null, inbox: null })]);

    expect(totals).toEqual({ conversations: 6, bookings: 4, waiting: 6, value: { minor: 1500, currency: "GEL" } });
  });

  it("names no money total across currencies", () => {
    expect(brandTotals([row({ currency: "GEL" }), row({ currency: "EUR" })]).value).toBeNull();
  });

  it("names no money total when a location shows no money (a manager's view)", () => {
    const totals = brandTotals([row({ revenue: 1000 }), row({ revenue: null })]);

    expect(totals.value).toBeNull();
    expect(totals.conversations).toBe(6);
  });
});

const invite = (extra: Partial<InviteForm> = {}): InviteForm => ({
  method: "phone",
  phone: "+995 555 77 00 01",
  countryHint: "GE",
  email: "",
  displayName: "",
  role: "regional_manager",
  businessIds: ["business_1"],
  ...extra,
});

describe("where a location's customers came from", () => {
  const sources = (counts: number[]) => ({
    business_id: "b",
    currency_code: "GEL",
    date_from: "2026-09-12",
    date_to: "2026-10-11",
    value_basis: "bookings" as const,
    rows: counts.map((count, index) => ({
      kind: "tagged" as const,
      acquisition_source: `tag-${index}`,
      conversation_count: count,
      booking_count: 0,
      request_count: 0,
      source_count: 1,
    })),
  });

  it("names the three that brought the most conversations", () => {
    expect(topSources(sources([9, 5, 3, 1])).map((row) => row.acquisition_source)).toEqual(["tag-0", "tag-1", "tag-2"]);
  });

  it("names none for a manager (no sources sent) or a period without conversations", () => {
    expect(topSources(null)).toEqual([]);
    expect(topSources(sources([0]))).toEqual([]);
  });
});

describe("brand invitations", () => {
  it("sends a manager's locations and a phone number", () => {
    const built = buildBrandInvite(invite({ displayName: " Nino " }));

    expect(built).toEqual({
      ok: true,
      body: {
        role: "regional_manager",
        business_ids: ["business_1"],
        phone_number: "+995 555 77 00 01",
        country_hint: "GE",
        display_name: "Nino",
      },
    });
  });

  it("refuses a manager without locations and a missing contact", () => {
    expect(buildBrandInvite(invite({ phone: " ", businessIds: [] }))).toEqual({
      ok: false,
      problems: { contact: "required", locations: "locations" },
    });
  });

  it("gives a brand owner every location, so none are sent", () => {
    const built = buildBrandInvite(invite({ role: "brand_owner", method: "email", email: "owner@example.com" }));

    expect(built).toMatchObject({ ok: true, body: { role: "brand_owner", business_ids: [], email: "owner@example.com" } });
  });

  it("checks the e-mail's shape", () => {
    expect(buildBrandInvite(invite({ method: "email", email: "nope" }))).toMatchObject({ ok: false, problems: { contact: "email" } });
  });
});

describe("prices typed by the owner", () => {
  it("reads commas and points into minor units", () => {
    expect(parsePriceMinor("12,50", 2)).toBe(1250);
    expect(parsePriceMinor("18", 2)).toBe(1800);
    expect(parsePriceMinor("", 2)).toBeNull();
    expect(parsePriceMinor("abc", 2)).toBeNaN();
  });
});
