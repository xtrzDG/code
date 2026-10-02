/**
 * Pure helpers of the Settings page: the settings form and its PATCH body,
 * team members, notification contacts, customer data requests and the
 * audit log.
 */

import type { ApiError } from "@/api/errors";
import type { RequestBody, Schema } from "@/api/types";
import type { BadgeTone } from "@/components/ui";

export type BusinessView = Schema<"BusinessView">;
export type BusinessMember = Schema<"BusinessMemberView">;
export type ManagerContact = Schema<"ManagerContactView">;
export type ManagerContactChannel = Schema<"ManagerContactChannel">;
export type AuditLogEntry = Schema<"AuditLogEntryView">;
export type AuditAction = Schema<"AuditAction">;
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

// --- Concurrent saves ----------------------------------------------------------

/** The API's reason for a settings save made from an older revision of the business. */
export const STALE_REVISION_REASON = "stale_revision";

/**
 * The PATCH body for changes made to `business` as it was shown: the API
 * applies them only while nobody has saved the business since (another
 * owner, another tab, a manager added by the Telegram bot).
 */
export function changesFromRevision(changes: SettingsChanges, business: Pick<BusinessView, "revision">): SettingsChanges {
  return { ...changes, expected_revision: business.revision };
}

/** True when a save was refused because the business changed after it was shown. */
export function isStaleRevision(error: ApiError): boolean {
  return error.status === 409 && error.reasons.some((reason) => reason.code === STALE_REVISION_REASON);
}

/**
 * The business the General form edits after this tab's own status switch
 * (`switched`: the view that save returned). The switch changes no field of
 * the form, so the form takes over its newer revision. If form fields differ
 * too, someone else saved in between: the form keeps what it loaded, and its
 * next save is refused as stale (it then reloads) instead of overwriting.
 */
export function afterStatusSwitch(loaded: BusinessView, switched: BusinessView | null): BusinessView {
  if (!switched || switched.revision <= loaded.revision) {
    return loaded;
  }
  const isSameForm = JSON.stringify(generalFormFrom(switched)) === JSON.stringify(generalFormFrom(loaded));
  return isSameForm ? switched : loaded;
}

export interface RebasedGeneralForm {
  form: GeneralForm;
  /** Fields changed both here and elsewhere: they now show the stored value. */
  conflicts: GeneralField[];
}

function sameFormValue(left: GeneralForm[GeneralField], right: GeneralForm[GeneralField]): boolean {
  return Array.isArray(left) && Array.isArray(right) ? sameList(left, right) : left === right;
}

/**
 * After a save refused as stale: the business as stored now (`latest`)
 * with the owner's own changes (the form against `shown`) on top. A field
 * someone else changed too takes the stored value and is reported; a
 * revision raised by an unrelated save (a manager linked, billing) keeps
 * everything that was typed.
 */
export function rebaseGeneralForm(shown: BusinessView, latest: BusinessView, form: GeneralForm): RebasedGeneralForm {
  const before = generalFormFrom(shown);
  const stored = generalFormFrom(latest);
  const next: Record<GeneralField, GeneralForm[GeneralField]> = { ...stored };
  const conflicts: GeneralField[] = [];
  for (const field of Object.keys(before) as GeneralField[]) {
    if (sameFormValue(form[field], before[field])) {
      continue;
    }
    if (sameFormValue(stored[field], before[field]) || sameFormValue(stored[field], form[field])) {
      next[field] = form[field];
    } else {
      conflicts.push(field);
    }
  }
  return { form: next as unknown as GeneralForm, conflicts };
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

/** A business always keeps one owner: the last owner can be neither removed nor made staff. */
export function canRemoveMember(member: BusinessMember, members: readonly BusinessMember[]): boolean {
  if (member.role !== "owner") {
    return true;
  }
  return members.filter((item) => item.role === "owner").length > 1;
}

export type MemberRole = BusinessMember["role"];

/** The roles a member may get now: staff only while another owner remains. */
export function allowedRoles(member: BusinessMember, members: readonly BusinessMember[]): MemberRole[] {
  return canRemoveMember(member, members) ? ["owner", "staff"] : ["owner"];
}

export type InviteMethod = "phone" | "email";

export interface InviteForm {
  method: InviteMethod;
  phone: string;
  countryHint: string;
  email: string;
  displayName: string;
  role: MemberRole;
}

export type InviteBody = RequestBody<"/v1/businesses/{business_id}/members", "post">;
export type InviteError = "required" | "email";

/** A loose e-mail shape check; the API validates for real. */
const EMAIL = /^[^\s@]+@[^\s@]+\.[^\s@]{2,}$/;

export function buildInviteBody(
  form: InviteForm,
): { ok: true; body: InviteBody } | { ok: false; errors: Partial<Record<"phone" | "email", InviteError>> } {
  const displayName = form.displayName.trim();
  const named = { ...(displayName ? { display_name: displayName } : {}), role: form.role };
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

/** A contact is known by its channel and address (not by its place in a list). */
export interface ContactKey {
  channel: ManagerContactChannel;
  address: string;
}

export type ContactChange =
  | { kind: "add"; contact: ManagerContactInput }
  | { kind: "edit"; original: ContactKey; contact: ManagerContactInput }
  | { kind: "remove"; original: ContactKey };

export function contactKey(contact: ContactKey): ContactKey {
  return { channel: contact.channel, address: contact.address };
}

function isSameContact(a: ContactKey, b: ContactKey): boolean {
  return a.channel === b.channel && a.address === b.address;
}

/**
 * The list to save: one change applied, by key, to the contacts as the tab
 * shows them. The API replaces the whole list, and contacts can change
 * meanwhile (another owner, a manager who opens the Telegram bot link is
 * added on the server), so the list is saved with the revision it was
 * shown at: a newer save is never overwritten; the tab reloads instead.
 */
export function applyContactChange(shown: readonly ManagerContact[], change: ContactChange): ManagerContactInput[] {
  const list = contactsToInput(shown);
  if (change.kind === "add") {
    return [...list, change.contact];
  }
  if (change.kind === "remove") {
    return list.filter((contact) => !isSameContact(contact, change.original));
  }
  const index = list.findIndex((contact) => isSameContact(contact, change.original));
  return index === -1 ? [...list, change.contact] : list.map((contact, at) => (at === index ? change.contact : contact));
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

export type ContactSummary = Schema<"ContactSummaryView">;
export type ContactPage = Schema<"ContactPage">;
export type ErasureResult = Schema<"ContactErasureResult">;

export const CONTACTS_PAGE_SIZE = 20;

/** What the owner types to confirm an erasure: the name, else the phone, else the id. */
export function erasureConfirmation(contact: Pick<ContactSummary, "id" | "name" | "phone_number">): string {
  return contact.name?.trim() || contact.phone_number || contact.id;
}

/** The customer as the list shows them after an erasure (nothing personal left). */
export function markErased(contact: ContactSummary, erasedAt: number): ContactSummary {
  return { ...contact, name: null, phone_number: null, is_phone_verified: false, language: null, erased_at: erasedAt };
}

/** The search sent to the API: trimmed, at most 100 characters, nothing for an empty box. */
export function contactSearchParam(text: string): string | undefined {
  const trimmed = text.trim().slice(0, 100);
  return trimmed === "" ? undefined : trimmed;
}

// --- Audit log --------------------------------------------------------------

export type AuditLogPage = Schema<"AuditLogPage">;

export const AUDIT_PAGE_SIZE = 50;

export interface AuditFilters {
  action: AuditAction | "";
  entity: string;
  actorId: string;
  /** Business-local days "YYYY-MM-DD" (inclusive), or "". */
  from: string;
  to: string;
}

export const EMPTY_AUDIT_FILTERS: AuditFilters = { action: "", entity: "", actorId: "", from: "", to: "" };

export function hasAuditFilters(filters: AuditFilters): boolean {
  return Object.values(filters).some((value) => value !== "");
}

/**
 * The query of GET …/audit-log for the filters: business-local days become
 * UTC microseconds, `until` is the start of the day after `to`.
 */
export function auditQuery(
  filters: AuditFilters,
  dayStartUs: (day: string) => number | null,
): { action?: AuditAction; entity?: string; actor_id?: string; since?: string; until?: string } {
  const since = filters.from ? dayStartUs(filters.from) : null;
  const until = filters.to ? dayStartUs(nextDay(filters.to)) : null;
  return {
    ...(filters.action ? { action: filters.action } : {}),
    ...(filters.entity ? { entity: filters.entity } : {}),
    ...(filters.actorId ? { actor_id: filters.actorId } : {}),
    ...(since !== null ? { since: String(since) } : {}),
    ...(until !== null ? { until: String(until) } : {}),
  };
}

/** "2026-02-28" -> "2026-03-01" (calendar arithmetic, no time zone). */
export function nextDay(day: string): string {
  const [year = 1970, month = 1, date = 1] = day.split("-").map(Number);
  const next = new Date(Date.UTC(year, month - 1, date + 1));
  return next.toISOString().slice(0, 10);
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
