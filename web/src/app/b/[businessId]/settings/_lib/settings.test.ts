import { describe, expect, it } from "vitest";

import {
  EMPTY_AUDIT_FILTERS,
  actorLabel,
  allowedRoles,
  auditQuery,
  buildGeneralChanges,
  buildInviteBody,
  canRemoveMember,
  contactFromForm,
  contactSearchParam,
  contactsToInput,
  erasureConfirmation,
  generalFormFrom,
  hasAuditFilters,
  hasChanges,
  languageChoices,
  markErased,
  memberInitials,
  memberLabel,
  nextDay,
  parseRetentionDays,
  sortMembers,
  toggleLanguage,
  validateContact,
  type BusinessMember,
  type BusinessView,
  type ContactSummary,
} from "./settings";

const member = (overrides: Partial<BusinessMember>): BusinessMember => ({
  user_id: "user_1",
  role: "staff",
  display_name: null,
  phone_number: null,
  email: null,
  is_verified: true,
  ...overrides,
});

const business: BusinessView = {
  id: "business_1",
  name: "Café Tbilisi",
  niche_key: "restaurant",
  country_code: "GE",
  city: "Tbilisi",
  timezone: "Asia/Tbilisi",
  currency_code: "GEL",
  languages: ["ka", "en"],
  default_language: "ka",
  owner_language: "ka",
  plan_key: "voice_and_chat",
  status: "live",
  service_mode: "full",
  data_region: "eu",
  recording_retention_days: 90,
  members: [member({ user_id: "user_owner", role: "owner", display_name: "Dato" })],
  manager_contacts: [],
  published_assistant_version_id: null,
  viewer_role: "owner",
  created_at: 1,
};

describe("general settings", () => {
  it("sends nothing when nothing changed", () => {
    const result = buildGeneralChanges(business, generalFormFrom(business));
    expect(result).toEqual({ ok: true, changes: {} });
    expect(result.ok && hasChanges(result.changes)).toBe(false);
  });

  it("sends only the changed fields, trimmed", () => {
    const form = { ...generalFormFrom(business), name: "  Café Rustaveli ", city: "", retentionDays: "30" };
    expect(buildGeneralChanges(business, form)).toEqual({
      ok: true,
      changes: { name: "Café Rustaveli", city: "", recording_retention_days: 30 },
    });
  });

  it("moves the default language when it is no longer spoken", () => {
    const form = { ...generalFormFrom(business), languages: ["en", "ru"] };
    expect(buildGeneralChanges(business, form)).toEqual({
      ok: true,
      changes: { languages: ["en", "ru"], default_language: "en" },
    });
  });

  it("refuses an empty name, no languages and a bad retention", () => {
    const form = { ...generalFormFrom(business), name: " ", languages: [], retentionDays: "0" };
    expect(buildGeneralChanges(business, form)).toEqual({
      ok: false,
      errors: { name: "required", languages: "languages", retentionDays: "retention" },
    });
    expect(buildGeneralChanges(business, { ...generalFormFrom(business), city: "x".repeat(121) })).toEqual({
      ok: false,
      errors: { city: "tooLong" },
    });
  });

  it("parses retention days in 1..3650", () => {
    expect(parseRetentionDays("90")).toBe(90);
    expect(parseRetentionDays(" 3650 ")).toBe(3650);
    expect(parseRetentionDays("3651")).toBeNull();
    expect(parseRetentionDays("1.5")).toBeNull();
    expect(parseRetentionDays("")).toBeNull();
  });

  it("merges and toggles languages in a stable order", () => {
    const choices = languageChoices(["ka", "en"], ["ka", "ru", "en"], ["tr"]);
    expect(choices).toEqual(["ka", "en", "ru", "tr"]);
    expect(toggleLanguage(["en"], "ka", true, choices)).toEqual(["ka", "en"]);
    expect(toggleLanguage(["ka", "en"], "ka", false, choices)).toEqual(["en"]);
    expect(toggleLanguage(["ka"], "fr", true, choices)).toEqual(["ka", "fr"]);
  });
});

describe("team", () => {
  const owner = member({ user_id: "u1", role: "owner", display_name: "Dato" });
  const staff = member({ user_id: "u2", phone_number: "+995555654321" });
  const emailOnly = member({ user_id: "u3", email: "giorgi@example.com" });

  it("labels members by name, phone or e-mail", () => {
    expect(memberLabel(owner)).toBe("Dato");
    expect(memberLabel(staff)).toBe("+995555654321");
    expect(memberLabel(emailOnly)).toBe("giorgi@example.com");
  });

  it("makes initials from display names only", () => {
    expect(memberInitials({ display_name: "Nino Beridze" })).toBe("NB");
    expect(memberInitials({ display_name: "ნინო" })).toBe("ნ");
    expect(memberInitials({ display_name: "  " })).toBeNull();
    expect(memberInitials({ display_name: null })).toBeNull();
  });

  it("lists owners first", () => {
    expect(sortMembers([staff, owner, emailOnly]).map((item) => item.user_id)).toEqual(["u1", "u2", "u3"]);
  });

  it("keeps the last owner", () => {
    expect(canRemoveMember(owner, [owner, staff])).toBe(false);
    expect(canRemoveMember(owner, [owner, member({ user_id: "u4", role: "owner" })])).toBe(true);
    expect(canRemoveMember(staff, [owner, staff])).toBe(true);
    expect(allowedRoles(owner, [owner, staff])).toEqual(["owner"]);
    expect(allowedRoles(owner, [owner, member({ user_id: "u4", role: "owner" })])).toEqual(["owner", "staff"]);
    expect(allowedRoles(staff, [owner, staff])).toEqual(["owner", "staff"]);
  });

  it("builds invitations by phone or e-mail with a role", () => {
    const base = { method: "phone" as const, phone: "", countryHint: "ge", email: "", displayName: "", role: "staff" as const };
    expect(buildInviteBody(base)).toEqual({ ok: false, errors: { phone: "required" } });
    expect(buildInviteBody({ ...base, phone: "555 65 43 21", displayName: " Nino " })).toEqual({
      ok: true,
      body: { phone_number: "555 65 43 21", country_hint: "GE", display_name: "Nino", role: "staff" },
    });
    expect(buildInviteBody({ ...base, method: "email", email: "nino@" })).toEqual({ ok: false, errors: { email: "email" } });
    expect(buildInviteBody({ ...base, method: "email", email: " nino@example.com ", role: "owner" })).toEqual({
      ok: true,
      body: { email: "nino@example.com", role: "owner" },
    });
  });
});

describe("notification contacts", () => {
  const existing = [{ name: "Nino", channel: "email" as const, address: "nino@example.com", language: "ka" }];

  it("checks names and addresses per channel", () => {
    expect(validateContact({ name: "", channel: "email", address: "", language: "ka" }, [])).toEqual({
      name: "required",
      address: "required",
    });
    expect(validateContact({ name: "Levan", channel: "email", address: "levan", language: "ka" }, [])).toEqual({
      address: "email",
    });
    expect(validateContact({ name: "Levan", channel: "telegram", address: "@levan", language: "ka" }, [])).toEqual({
      address: "chatId",
    });
    expect(validateContact({ name: "Levan", channel: "telegram", address: "-100123", language: "ka" }, [])).toEqual({});
    expect(validateContact({ name: "Levan", channel: "whatsapp", address: "599 11 22 33", language: "ka" }, [])).toEqual({});
  });

  it("refuses the same address twice", () => {
    expect(validateContact({ name: "N", channel: "email", address: "NINO@example.com", language: "ka" }, existing)).toEqual({
      address: "duplicate",
    });
  });

  it("maps contacts to the PATCH input", () => {
    expect(contactsToInput(existing)).toEqual(existing);
    expect(contactFromForm({ name: " Levan ", channel: "sms", address: " 599 ", language: "ru" })).toEqual({
      name: "Levan",
      channel: "sms",
      address: "599",
      language: "ru",
    });
  });
});

describe("customer data requests", () => {
  const contact = (overrides: Partial<ContactSummary> = {}): ContactSummary => ({
    id: "contact_a",
    name: "Ana",
    phone_number: "+995599112233",
    is_phone_verified: true,
    language: "ka",
    channels: ["telegram"],
    conversation_count: 2,
    booking_count: 1,
    lead_count: 0,
    first_seen_at: 1,
    last_activity_at: 10,
    erased_at: null,
    ...overrides,
  });

  it("asks to type the name, else the phone, else the id", () => {
    expect(erasureConfirmation({ id: "contact_a", name: " Ana ", phone_number: "+1" })).toBe("Ana");
    expect(erasureConfirmation({ id: "contact_a", name: null, phone_number: "+995599112233" })).toBe("+995599112233");
    expect(erasureConfirmation({ id: "contact_a", name: null, phone_number: null })).toBe("contact_a");
  });

  it("shows an erased customer without personal data", () => {
    expect(markErased(contact(), 99)).toEqual(
      contact({ name: null, phone_number: null, is_phone_verified: false, language: null, erased_at: 99 }),
    );
  });

  it("sends a trimmed search, or none", () => {
    expect(contactSearchParam("  599 11 ")).toBe("599 11");
    expect(contactSearchParam("   ")).toBeUndefined();
    expect(contactSearchParam("x".repeat(150))).toHaveLength(100);
  });
});

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
