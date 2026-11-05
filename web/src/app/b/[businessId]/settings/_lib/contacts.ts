/** Pure helpers of the Settings page's Notifications tab: the manager contacts. */

import type { Schema } from "@/api/types";

import type { SettingsChanges } from "./general";
import { isEverything, preferencesFromForm, type PreferencesForm } from "./notifications";
import { EMAIL } from "./team";

export type ManagerContact = Schema<"ManagerContactView">;
export type ManagerContactChannel = Schema<"ManagerContactChannel">;

export const MAX_MANAGER_CONTACTS = 20;
export const MAX_MANAGER_NAME_LENGTH = 100;

export type ManagerContactInput = NonNullable<SettingsChanges["manager_contacts"]>[number];

export interface ContactForm {
  name: string;
  channel: ManagerContactChannel;
  address: string;
  language: string;
  /** Which events reach the contact and their quiet hours (absent: every event, at any hour). */
  preferences?: PreferencesForm;
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

/**
 * The stored contacts as the PATCH input (the list is replaced as a
 * whole, so every contact's choices go with it; the server keeps the
 * Telegram @username of a linked chat by itself).
 */
export function contactsToInput(contacts: readonly ManagerContact[]): ManagerContactInput[] {
  return contacts.map((contact) => ({
    name: contact.name,
    channel: contact.channel,
    address: contact.address,
    language: contact.language,
    ...(contact.preferences ? { preferences: contact.preferences } : {}),
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
  const preferences = form.preferences ? preferencesFromForm(form.preferences) : null;
  return {
    name: form.name.trim(),
    channel: form.channel,
    address: form.address.trim(),
    language: form.language,
    ...(preferences && !isEverything(preferences) ? { preferences } : {}),
  };
}
