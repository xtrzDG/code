/** Pure helpers of the Settings page's Privacy tab: customer data requests. */

import type { Schema } from "@/api/types";

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
