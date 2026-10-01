/**
 * Pure helpers of the Settings page: the settings form and its PATCH body,
 * team members, notification contacts, customer data requests and the
 * audit log.
 */

import type { RequestBody, Schema } from "@/api/types";
import type { BadgeTone } from "@/components/ui";

export type BusinessView = Schema<"BusinessView">;
export type BusinessMember = Schema<"BusinessMemberView">;
export type ManagerContact = Schema<"ManagerContactView">;
export type ManagerContactChannel = Schema<"ManagerContactChannel">;
export type AuditLogEntry = Schema<"AuditLogEntryView">;
export type AuditAction = Schema<"AuditAction">;
export type ConversationSummary = Schema<"ConversationSummaryView">;
export type SettingsChanges = RequestBody<"/v1/businesses/{business_id}", "patch">;

export const MAX_BUSINESS_NAME_LENGTH = 200;
export const MAX_CITY_LENGTH = 120;
export const MIN_RETENTION_DAYS = 1;
export const MAX_RETENTION_DAYS = 3650;
export const MAX_MANAGER_CONTACTS = 20;
export const MAX_MANAGER_NAME_LENGTH = 100;

// --- General settings --------------------------------------------------------

export interface GeneralForm {
  name: string;
  city: string;
  timezone: string;
  languages: string[];
  defaultLanguage: string;
  ownerLanguage: string;
  retentionDays: string;
}

export type GeneralField = keyof GeneralForm;
export type GeneralError = "required" | "tooLong" | "languages" | "retention";

export function generalFormFrom(business: BusinessView): GeneralForm {
  return {
    name: business.name,
    city: business.city ?? "",
    timezone: business.timezone,
    languages: [...business.languages],
    defaultLanguage: business.default_language,
    ownerLanguage: business.owner_language,
    retentionDays: String(business.recording_retention_days),
  };
}

/** "90" -> 90; anything that is not a whole number in 1..3650 -> null. */
export function parseRetentionDays(text: string): number | null {
  const trimmed = text.trim();
  if (!/^\d+$/.test(trimmed)) {
    return null;
  }
  const days = Number(trimmed);
  return days >= MIN_RETENTION_DAYS && days <= MAX_RETENTION_DAYS ? days : null;
}

function sameList(left: readonly string[], right: readonly string[]): boolean {
  return left.length === right.length && left.every((value, index) => value === right[index]);
}

export type GeneralResult =
  | { ok: true; changes: SettingsChanges }
  | { ok: false; errors: Partial<Record<GeneralField, GeneralError>> };

/**
 * The PATCH body with only the fields that changed, or the fields to fix.
 * A default language that dropped out of the list falls back to the first one.
 */
export function buildGeneralChanges(business: BusinessView, form: GeneralForm): GeneralResult {
  const errors: Partial<Record<GeneralField, GeneralError>> = {};
  const name = form.name.trim();
  const city = form.city.trim();
  if (name === "") {
    errors.name = "required";
  } else if (name.length > MAX_BUSINESS_NAME_LENGTH) {
    errors.name = "tooLong";
  }
  if (city.length > MAX_CITY_LENGTH) {
    errors.city = "tooLong";
  }
  if (form.languages.length === 0) {
    errors.languages = "languages";
  }
  const retention = parseRetentionDays(form.retentionDays);
  if (retention === null) {
    errors.retentionDays = "retention";
  }
  if (Object.keys(errors).length > 0 || retention === null) {
    return { ok: false, errors };
  }

  const defaultLanguage = form.languages.includes(form.defaultLanguage) ? form.defaultLanguage : form.languages[0];
  const changes: SettingsChanges = {};
  if (name !== business.name) {
    changes.name = name;
  }
  if (city !== (business.city ?? "")) {
    changes.city = city;
  }
  if (form.timezone !== business.timezone) {
    changes.timezone = form.timezone;
  }
  if (!sameList(form.languages, business.languages)) {
    changes.languages = form.languages;
  }
  if (defaultLanguage && defaultLanguage !== business.default_language) {
    changes.default_language = defaultLanguage;
  }
  if (form.ownerLanguage !== business.owner_language) {
    changes.owner_language = form.ownerLanguage;
  }
  if (retention !== business.recording_retention_days) {
    changes.recording_retention_days = retention;
  }
  return { ok: true, changes };
}

export function hasChanges(changes: SettingsChanges): boolean {
  return Object.keys(changes).length > 0;
}

/** Languages to offer: the business's own first, then the others, without repeats. */
export function languageChoices(...groups: readonly (readonly string[])[]): string[] {
  return [...new Set(groups.flat())];
}

/** Toggle a language and keep the order of `choices`. */
export function toggleLanguage(selected: readonly string[], tag: string, isOn: boolean, choices: readonly string[]): string[] {
  const next = new Set(selected);
  if (isOn) {
    next.add(tag);
  } else {
    next.delete(tag);
  }
  const ordered = choices.filter((choice) => next.has(choice));
  const rest = [...next].filter((choice) => !choices.includes(choice));
  return [...ordered, ...rest];
}

// --- Team ------------------------------------------------------------------

/** The name to show for a member: display name, else phone, else e-mail. */
export function memberLabel(member: Pick<BusinessMember, "display_name" | "phone_number" | "email">): string {
  return member.display_name || member.phone_number || member.email || "";
}

/** Up to two initials of a member's display name ("Nino Beridze" -> "NB"), or null without a name. */
export function memberInitials(member: Pick<BusinessMember, "display_name">): string | null {
  const parts = (member.display_name ?? "").trim().split(/\s+/).filter(Boolean);
  if (parts.length === 0) {
    return null;
  }
  // Georgian has no capital letters in normal text (Mtavruli is for headings).
  const capital = (letter: string) => (/[\u10A0-\u10FF]/.test(letter) ? letter : letter.toLocaleUpperCase());
  return parts
    .slice(0, 2)
    .map((part) => capital([...part][0] ?? ""))
    .join("");
}

/** Owners first, then by name. */
export function sortMembers(members: readonly BusinessMember[]): BusinessMember[] {
  return [...members].sort((left, right) => {
    if (left.role !== right.role) {
      return left.role === "owner" ? -1 : 1;
    }
    return memberLabel(left).localeCompare(memberLabel(right));
  });
}

/** A business always keeps one owner: the last owner cannot be removed. */
export function canRemoveMember(member: BusinessMember, members: readonly BusinessMember[]): boolean {
  if (member.role !== "owner") {
    return true;
  }
  return members.filter((item) => item.role === "owner").length > 1;
}

export type InviteMethod = "phone" | "email";

export interface InviteForm {
  method: InviteMethod;
  phone: string;
  countryHint: string;
  email: string;
  displayName: string;
}

export type InviteBody = RequestBody<"/v1/businesses/{business_id}/members", "post">;
export type InviteError = "required" | "email";

/** A loose e-mail shape check; the API validates for real. */
const EMAIL = /^[^\s@]+@[^\s@]+\.[^\s@]{2,}$/;

export function buildInviteBody(
  form: InviteForm,
): { ok: true; body: InviteBody } | { ok: false; errors: Partial<Record<"phone" | "email", InviteError>> } {
  const displayName = form.displayName.trim();
  const named = displayName ? { display_name: displayName } : {};
  if (form.method === "phone") {
    const phone = form.phone.trim();
    if (phone === "") {
      return { ok: false, errors: { phone: "required" } };
    }
    const hint = form.countryHint.trim().toUpperCase();
    return {
      ok: true,
      body: { phone_number: phone, ...(/^[A-Z]{2}$/.test(hint) ? { country_hint: hint } : {}), ...named },
    };
  }
  const email = form.email.trim();
  if (email === "") {
    return { ok: false, errors: { email: "required" } };
  }
  if (!EMAIL.test(email)) {
    return { ok: false, errors: { email: "email" } };
  }
  return { ok: true, body: { email, ...named } };
}

// --- Notification contacts ---------------------------------------------------

export type ManagerContactInput = NonNullable<SettingsChanges["manager_contacts"]>[number];

export interface ContactForm {
  name: string;
  channel: ManagerContactChannel;
  address: string;
  language: string;
}

export type ContactField = "name" | "address";
export type ContactError = "required" | "tooLong" | "email" | "chatId" | "duplicate";

const TELEGRAM_CHAT_ID = /^-?\d{1,20}$/;

/** Check one contact before the whole list is sent (the API checks again). */
export function validateContact(
  form: ContactForm,
  others: readonly ManagerContact[],
): Partial<Record<ContactField, ContactError>> {
  const errors: Partial<Record<ContactField, ContactError>> = {};
  const name = form.name.trim();
  const address = form.address.trim();
  if (name === "") {
    errors.name = "required";
  } else if (name.length > MAX_MANAGER_NAME_LENGTH) {
    errors.name = "tooLong";
  }
  if (address === "") {
    errors.address = "required";
  } else if (form.channel === "email" && !EMAIL.test(address)) {
    errors.address = "email";
  } else if (form.channel === "telegram" && !TELEGRAM_CHAT_ID.test(address)) {
    errors.address = "chatId";
  } else if (
    others.some(
      (contact) =>
        contact.channel === form.channel && contact.address.toLocaleLowerCase() === address.toLocaleLowerCase(),
    )
  ) {
    errors.address = "duplicate";
  }
  return errors;
}

/** The stored contacts as the PATCH input (the list is replaced as a whole). */
export function contactsToInput(contacts: readonly ManagerContact[]): ManagerContactInput[] {
  return contacts.map((contact) => ({
    name: contact.name,
    channel: contact.channel,
    address: contact.address,
    language: contact.language,
  }));
}

export function contactFromForm(form: ContactForm): ManagerContactInput {
  return {
    name: form.name.trim(),
    channel: form.channel,
    address: form.address.trim(),
    language: form.language,
  };
}

// --- Customer data requests ------------------------------------------------

export interface CustomerContact {
  contactId: string;
  name: string | null;
  phoneNumber: string | null;
  lastMessageAt: number;
  conversationCount: number;
  channels: ConversationSummary["channel"][];
}

/** One row per customer from the conversation list, latest activity first. */
export function contactsFromConversations(conversations: readonly ConversationSummary[]): CustomerContact[] {
  const byId = new Map<string, CustomerContact>();
  for (const conversation of conversations) {
    const existing = byId.get(conversation.contact_id);
    if (!existing) {
      byId.set(conversation.contact_id, {
        contactId: conversation.contact_id,
        name: conversation.contact_name ?? null,
        phoneNumber: conversation.contact_phone_number ?? null,
        lastMessageAt: conversation.last_message_at,
        conversationCount: 1,
        channels: [conversation.channel],
      });
      continue;
    }
    existing.conversationCount += 1;
    existing.name ??= conversation.contact_name ?? null;
    existing.phoneNumber ??= conversation.contact_phone_number ?? null;
    existing.lastMessageAt = Math.max(existing.lastMessageAt, conversation.last_message_at);
    if (!existing.channels.includes(conversation.channel)) {
      existing.channels.push(conversation.channel);
    }
  }
  return [...byId.values()].sort((left, right) => right.lastMessageAt - left.lastMessageAt);
}

/** Customers matching a search by name, phone digits or id. */
export function filterCustomers(customers: readonly CustomerContact[], query: string): CustomerContact[] {
  const needle = query.trim().toLocaleLowerCase();
  if (needle === "") {
    return [...customers];
  }
  const digits = needle.replace(/\D/g, "");
  return customers.filter(
    (customer) =>
      (customer.name ?? "").toLocaleLowerCase().includes(needle) ||
      customer.contactId.toLocaleLowerCase().includes(needle) ||
      (digits.length >= 3 && (customer.phoneNumber ?? "").replace(/\D/g, "").includes(digits)),
  );
}

/** What the owner types to confirm an erasure: the name, else the phone, else the id. */
export function erasureConfirmation(customer: Pick<CustomerContact, "contactId" | "name" | "phoneNumber">): string {
  return customer.name?.trim() || customer.phoneNumber || customer.contactId;
}

/** A contact id typed or pasted by the owner ("contact_…"), or null. */
export function parseContactId(text: string): string | null {
  const trimmed = text.trim();
  return /^contact_[0-9a-f-]{8,}$/i.test(trimmed) ? trimmed : null;
}

// --- Audit log --------------------------------------------------------------

export const AUDIT_PAGE_SIZE = 50;
export const AUDIT_MAX_LIMIT = 1000;

/** The next "show more" limit (the API returns the newest N entries). */
export function nextAuditLimit(current: number): number {
  return Math.min(AUDIT_MAX_LIMIT, current + AUDIT_PAGE_SIZE);
}

/** Whether more entries may exist beyond those loaded. */
export function hasMoreAudit(loaded: number, limit: number): boolean {
  return loaded >= limit && limit < AUDIT_MAX_LIMIT;
}

export const AUDIT_ACTION_TONES: Record<AuditAction, BadgeTone> = {
  view: "neutral",
  create: "success",
  update: "info",
  delete: "danger",
  export: "warning",
  admin_access: "accent",
  login: "neutral",
  retention_purge: "neutral",
  publish_untested: "warning",
};

/** Who did it: a team member's name, or null for the platform / unknown users. */
export function actorLabel(actorId: string | null | undefined, members: readonly BusinessMember[]): string | null {
  if (!actorId) {
    return null;
  }
  const member = members.find((item) => item.user_id === actorId);
  return member ? memberLabel(member) : null;
}
