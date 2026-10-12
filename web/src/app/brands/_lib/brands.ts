/**
 * Pure rules of the brand pages and the business switcher: memberships
 * grouped by brand, a brand's totals over its reached locations, the
 * businesses an owner can still put into a brand, and the forms' checks.
 */

import type { Schema, UserMembershipView } from "@/api/types";

export type BrandView = Schema<"BrandView">;
export type BrandLocationView = Schema<"BrandLocationView">;
export type BrandMemberView = Schema<"BrandMemberView">;
export type BrandMemberRole = Schema<"BrandMemberRole">;
export type BrandLocationDashboard = Schema<"BrandLocationDashboard">;
export type BrandKnowledgeItem = Schema<"BrandKnowledgeItemView">;

export const BRAND_ROLES = ["brand_owner", "regional_manager"] as const satisfies readonly BrandMemberRole[];

/** The kinds a brand shares (services, stays and offers stay each location's own). */
export const SHARED_KINDS = ["faq", "policy", "menu_item", "product"] as const;
export type SharedKind = (typeof SHARED_KINDS)[number];

export interface MembershipGroup {
  /** The brand, or null for the businesses outside any brand. */
  brand: { id: string; name: string } | null;
  memberships: UserMembershipView[];
}

/**
 * The switcher's groups: one per brand (in the order its first location
 * comes), then the businesses outside any brand. Without any brand there
 * is a single unnamed group, so the menu looks as it always did.
 */
export function groupMemberships(memberships: readonly UserMembershipView[]): MembershipGroup[] {
  const groups = new Map<string, MembershipGroup>();
  const others: UserMembershipView[] = [];
  for (const membership of memberships) {
    if (!membership.brand_id) {
      others.push(membership);
      continue;
    }
    const group = groups.get(membership.brand_id) ?? {
      brand: { id: membership.brand_id, name: membership.brand_name ?? "" },
      memberships: [],
    };
    group.memberships.push(membership);
    groups.set(membership.brand_id, group);
  }
  const branded = [...groups.values()];
  return others.length > 0 || branded.length === 0 ? [...branded, { brand: null, memberships: others }] : branded;
}

/** Businesses the person owns that belong to no brand yet: where a brand can start or grow. */
export function ownedFreeBusinesses(memberships: readonly UserMembershipView[]): UserMembershipView[] {
  return memberships.filter((membership) => membership.role === "owner" && !membership.brand_id);
}

export interface BrandTotals {
  conversations: number;
  bookings: number;
  waiting: number;
  /** The estimated value when every reached location has one, in one currency; else null. */
  value: { minor: number; currency: string } | null;
}

/** What the brand's reached locations add up to (locked ones count nothing). */
export function brandTotals(locations: readonly BrandLocationDashboard[]): BrandTotals {
  const totals: BrandTotals = { conversations: 0, bookings: 0, waiting: 0, value: null };
  const currencies = new Set<string>();
  let valueMinor = 0;
  let isValueComplete = true;
  for (const row of locations) {
    if (row.is_locked) {
      continue;
    }
    if (row.value) {
      const revenue = row.value.current.estimated_revenue_minor;
      totals.conversations += row.value.current.conversation_count;
      totals.bookings += row.value.current.assistant_booking_count;
      isValueComplete &&= revenue !== null && revenue !== undefined;
      valueMinor += revenue ?? 0;
      currencies.add(row.value.currency_code);
    }
    if (row.inbox) {
      totals.waiting += row.inbox.needs_person + row.inbox.requests;
    }
  }
  if (isValueComplete && currencies.size === 1) {
    totals.value = { minor: valueMinor, currency: [...currencies][0] ?? "" };
  }
  return totals;
}

export interface InviteForm {
  method: "phone" | "email";
  phone: string;
  countryHint: string;
  email: string;
  displayName: string;
  role: BrandMemberRole;
  businessIds: string[];
}

export type InviteProblem = "required" | "email" | "locations";

export interface InviteBody {
  role: BrandMemberRole;
  business_ids: string[];
  phone_number?: string;
  country_hint?: string;
  email?: string;
  display_name?: string;
}

const EMAIL = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;

/** The invitation's body, or what is missing: a manager runs at least one location. */
export function buildBrandInvite(
  form: InviteForm,
): { ok: true; body: InviteBody } | { ok: false; problems: Partial<Record<"contact" | "locations", InviteProblem>> } {
  const problems: Partial<Record<"contact" | "locations", InviteProblem>> = {};
  const phone = form.phone.trim();
  const email = form.email.trim();
  if (form.method === "phone" && phone === "") {
    problems.contact = "required";
  }
  if (form.method === "email" && (email === "" || !EMAIL.test(email))) {
    problems.contact = email === "" ? "required" : "email";
  }
  const isManager = form.role === "regional_manager";
  if (isManager && form.businessIds.length === 0) {
    problems.locations = "locations";
  }
  if (problems.contact || problems.locations) {
    return { ok: false, problems };
  }
  const displayName = form.displayName.trim();
  return {
    ok: true,
    body: {
      role: form.role,
      business_ids: isManager ? [...form.businessIds] : [],
      ...(form.method === "phone" ? { phone_number: phone, country_hint: form.countryHint } : { email }),
      ...(displayName ? { display_name: displayName } : {}),
    },
  };
}

/**
 * A price typed by the owner in minor units ("12,50" → 1250), for a
 * currency with `fractionDigits` decimals; null when empty, NaN when not
 * a price.
 */
export function parsePriceMinor(text: string, fractionDigits: number): number | null {
  const trimmed = text.trim().replace(/\s/g, "").replace(",", ".");
  if (trimmed === "") {
    return null;
  }
  if (!/^\d+(\.\d+)?$/.test(trimmed)) {
    return Number.NaN;
  }
  return Math.round(Number(trimmed) * 10 ** fractionDigits);
}

/** A member's name for lists and sentences: the name, else the phone, else the e-mail. */
export function brandMemberLabel(member: Pick<BrandMemberView, "display_name" | "phone_number" | "email">): string {
  return member.display_name ?? member.phone_number ?? member.email ?? "";
}
