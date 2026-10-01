import { describe, expect, it } from "vitest";

import {
  actorLabel,
  buildGeneralChanges,
  buildInviteBody,
  canRemoveMember,
  contactFromForm,
  contactsFromConversations,
  contactsToInput,
  erasureConfirmation,
  filterCustomers,
  generalFormFrom,
  hasChanges,
  hasMoreAudit,
  languageChoices,
  memberInitials,
  memberLabel,
  nextAuditLimit,
  parseContactId,
  parseRetentionDays,
  sortMembers,
  toggleLanguage,
  validateContact,
  type BusinessMember,
  type BusinessView,
  type ConversationSummary,
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
  });

  it("builds invitations by phone or e-mail", () => {
    const base = { method: "phone" as const, phone: "", countryHint: "ge", email: "", displayName: "" };
    expect(buildInviteBody(base)).toEqual({ ok: false, errors: { phone: "required" } });
    expect(buildInviteBody({ ...base, phone: "555 65 43 21", displayName: " Nino " })).toEqual({
      ok: true,
      body: { phone_number: "555 65 43 21", country_hint: "GE", display_name: "Nino" },
    });
    expect(buildInviteBody({ ...base, method: "email", email: "nino@" })).toEqual({ ok: false, errors: { email: "email" } });
    expect(buildInviteBody({ ...base, method: "email", email: " nino@example.com " })).toEqual({
      ok: true,
      body: { email: "nino@example.com" },
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
  const conversation = (overrides: Partial<ConversationSummary>): ConversationSummary => ({
    id: "conversation_1",
    business_id: "business_1",
    assistant_version_id: "assistant_version_1",
    channel: "telegram",
    contact_id: "contact_a",
    contact_name: null,
    contact_phone_number: null,
    created_at: 1,
    is_after_hours: false,
    is_sandbox: false,
    language: null,
    last_message_at: 10,
    last_message_text: null,
    message_count: 1,
    customer_message_count: 1,
    status: "open",
    ...overrides,
  });

  it("groups conversations by customer, latest first", () => {
    const customers = contactsFromConversations([
      conversation({ id: "c1", contact_id: "contact_a", last_message_at: 10 }),
      conversation({ id: "c2", contact_id: "contact_b", contact_name: "Ana", last_message_at: 30, channel: "phone" }),
      conversation({ id: "c3", contact_id: "contact_a", contact_name: "Giorgi", contact_phone_number: "+995599112233", last_message_at: 20, channel: "whatsapp" }),
    ]);
    expect(customers).toEqual([
      { contactId: "contact_b", name: "Ana", phoneNumber: null, lastMessageAt: 30, conversationCount: 1, channels: ["phone"] },
      {
        contactId: "contact_a",
        name: "Giorgi",
        phoneNumber: "+995599112233",
        lastMessageAt: 20,
        conversationCount: 2,
        channels: ["telegram", "whatsapp"],
      },
    ]);
    expect(filterCustomers(customers, "gio").map((item) => item.contactId)).toEqual(["contact_a"]);
    expect(filterCustomers(customers, "599 11").map((item) => item.contactId)).toEqual(["contact_a"]);
    expect(filterCustomers(customers, "contact_b").map((item) => item.contactId)).toEqual(["contact_b"]);
    expect(filterCustomers(customers, " ")).toHaveLength(2);
  });

  it("asks to type the name, else the phone, else the id", () => {
    expect(erasureConfirmation({ contactId: "contact_a", name: " Ana ", phoneNumber: "+1" })).toBe("Ana");
    expect(erasureConfirmation({ contactId: "contact_a", name: null, phoneNumber: "+995599112233" })).toBe("+995599112233");
    expect(erasureConfirmation({ contactId: "contact_a", name: null, phoneNumber: null })).toBe("contact_a");
  });

  it("accepts pasted contact ids only", () => {
    expect(parseContactId(" contact_639833a1-4f05-440f-bbab-540dca7ac3b8 ")).toBe("contact_639833a1-4f05-440f-bbab-540dca7ac3b8");
    expect(parseContactId("user_639833a1")).toBeNull();
    expect(parseContactId("contact_")).toBeNull();
  });
});

describe("audit log", () => {
  it("pages by 50 up to 1000", () => {
    expect(nextAuditLimit(50)).toBe(100);
    expect(nextAuditLimit(980)).toBe(1000);
    expect(hasMoreAudit(50, 50)).toBe(true);
    expect(hasMoreAudit(12, 50)).toBe(false);
    expect(hasMoreAudit(1000, 1000)).toBe(false);
  });

  it("names actors who are team members", () => {
    const members = [member({ user_id: "u1", display_name: "Nino" })];
    expect(actorLabel("u1", members)).toBe("Nino");
    expect(actorLabel("u9", members)).toBeNull();
    expect(actorLabel(null, members)).toBeNull();
  });
});
