/**
 * Pure helpers of the Customers section: what a customer is called, their
 * phone as the viewer may see it (staff may get a masked one), the
 * standing line ("Regular customer · 4 visits"), the tags on a card and
 * erasing a customer's data.
 */

import type { RequestBody, Schema } from "@/api/types";
import { interpolate } from "@/i18n/translate";
import { interfaceSentence, type SentenceWithUserValues } from "@/i18n/userValues";
import { formatPhone } from "@/lib/phone";

export type CustomerSummary = Schema<"ContactSummaryView">;
export type CustomerPage = Schema<"ContactPage">;
export type CustomerDetail = Schema<"ContactDetailView">;
export type CustomerCard = Schema<"CustomerCardView">;
export type TimelineEntry = Schema<"CustomerTimelineEntry">;
export type CardChange = RequestBody<"/v1/businesses/{business_id}/contacts/{contact_id}/card", "patch">;

export const CUSTOMERS_PAGE_SIZE = 25;

/** The API's limits of a card. */
export const MAX_TAG_LENGTH = 32;
export const MAX_TAGS_PER_CUSTOMER = 20;
const TAG_SUGGESTIONS = 8;

type PhoneFields = Pick<CustomerSummary, "phone_number" | "masked_phone_number" | "is_phone_masked">;

/** The phone the viewer may see: the full number grouped for reading, else the masked one staff get. */
export function shownPhone(contact: PhoneFields): { text: string; isMasked: boolean } | null {
  if (contact.phone_number) {
    return { text: formatPhone(contact.phone_number), isMasked: false };
  }
  if (contact.masked_phone_number) {
    return { text: contact.masked_phone_number, isMasked: true };
  }
  return null;
}

/** What to call the customer: their name, else the phone they may see, else `unnamed`. */
export function customerName(contact: Pick<CustomerSummary, "name"> & PhoneFields, unnamed: string): string {
  return contact.name?.trim() || shownPhone(contact)?.text || unnamed;
}

/**
 * What a page calls the customer: their own name or phone (`isOwn`, user
 * content), or a label of ours ("No name", "Data erased").
 */
export interface CustomerNaming {
  name: string;
  isOwn: boolean;
}

/** The customer's own name or phone; one of `labels` (ours) for an erased or nameless customer. */
export function customerNaming(
  contact: Pick<CustomerSummary, "name" | "erased_at"> & PhoneFields,
  labels: { unnamed: string; erased: string },
): CustomerNaming {
  if (contact.erased_at) {
    return { name: labels.erased, isOwn: false };
  }
  const own = customerName(contact, "");
  return own ? { name: own, isOwn: true } : { name: labels.unnamed, isOwn: false };
}

/** A sentence of ours naming the customer ("Block {name}?"): their own name apart, as user content. */
export function namingSentence(template: string, naming: CustomerNaming): SentenceWithUserValues {
  return naming.isOwn
    ? { text: template, values: { name: naming.name } }
    : interfaceSentence(interpolate(template, { name: naming.name }));
}

/** What the owner types to confirm an erasure: the name, else the phone, else the id. */
export function erasureConfirmation(contact: Pick<CustomerSummary, "id" | "name" | "phone_number">): string {
  return contact.name?.trim() || contact.phone_number || contact.id;
}

/** The customer as the page shows them after an erasure (nothing personal, no card). */
export function markErased<Contact extends CustomerSummary>(contact: Contact, erasedAt: number): Contact {
  return {
    ...contact,
    name: null,
    phone_number: null,
    masked_phone_number: null,
    is_phone_verified: false,
    language: null,
    tags: [],
    is_vip: false,
    is_blocked: false,
    erased_at: erasedAt,
  };
}

/** A tag as typed: spaces at the ends and runs of spaces inside go, control characters too. */
export function cleanTag(text: string): string {
  return text
    .replace(/[\u0000-\u001f\u007f]/g, " ")
    .replace(/\s+/g, " ")
    .trim();
}

/** Tags compare without case, as the API compares them. */
function tagKey(tag: string): string {
  return tag.toLowerCase();
}

export function hasTag(tags: readonly string[], tag: string): boolean {
  const key = tagKey(tag);
  return tags.some((existing) => tagKey(existing) === key);
}

export type TagProblem = "empty" | "tooLong" | "tooMany" | "duplicate";

/** Why a typed tag cannot go on the card, or null when it can. */
export function tagProblem(text: string, tags: readonly string[]): TagProblem | null {
  const tag = cleanTag(text);
  if (tag === "") {
    return "empty";
  }
  if (tag.length > MAX_TAG_LENGTH) {
    return "tooLong";
  }
  if (hasTag(tags, tag)) {
    return "duplicate";
  }
  return tags.length >= MAX_TAGS_PER_CUSTOMER ? "tooMany" : null;
}

/** The business's tags the card lacks, those starting with what is typed first, at most eight. */
export function tagSuggestions(known: readonly string[], tags: readonly string[], typed: string): string[] {
  const prefix = tagKey(cleanTag(typed));
  const free = known.filter((tag) => !hasTag(tags, tag));
  const starting = free.filter((tag) => tagKey(tag).startsWith(prefix));
  const containing = prefix === "" ? [] : free.filter((tag) => !starting.includes(tag) && tagKey(tag).includes(prefix));
  return [...starting, ...containing].slice(0, TAG_SUGGESTIONS);
}

/** The card after a change, shown before the API answers. */
export function changedCard(card: CustomerCard, change: CardChange): CustomerCard {
  const removed = new Set((change.remove_tags ?? []).map(tagKey));
  const kept = (card.tags ?? []).filter((tag) => !removed.has(tagKey(tag)));
  const added = (change.add_tags ?? []).filter((tag) => !hasTag(kept, tag));
  return {
    ...card,
    tags: [...kept, ...added].slice(0, MAX_TAGS_PER_CUSTOMER),
    is_vip: change.is_vip ?? card.is_vip,
  };
}

/** The card of a customer page's data. */
export function cardOf(detail: CustomerDetail, knownTags: readonly string[] = []): CustomerCard {
  return {
    contact_id: detail.contact.id,
    tags: detail.contact.tags ?? [],
    is_vip: detail.contact.is_vip ?? false,
    is_blocked: detail.contact.is_blocked ?? false,
    blocked_at: detail.blocked_at ?? null,
    known_tags: [...knownTags],
  };
}

/** The customer page's data with the card the API answered. */
export function withCard(detail: CustomerDetail, card: CustomerCard): CustomerDetail {
  return {
    ...detail,
    blocked_at: card.blocked_at ?? null,
    contact: { ...detail.contact, tags: card.tags ?? [], is_vip: card.is_vip ?? false, is_blocked: card.is_blocked ?? false },
  };
}
