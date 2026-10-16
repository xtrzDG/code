/**
 * "Who handles hard questions": the ways the signed-in owner can be told
 * themselves (their sign-in phone by WhatsApp or SMS, their sign-in
 * e-mail), so the step offers them in one tap, and what is already set.
 */

import type { Schema } from "@/api/types";

type ManagerContactChannel = Schema<"ManagerContactChannel">;
type ManagerContactView = Schema<"ManagerContactView">;

export interface OwnerChoice {
  channel: ManagerContactChannel;
  address: string;
}

/**
 * The owner's own addresses as staff contact choices: WhatsApp first for
 * a phone (it shows urgent messages best), then SMS, then e-mail.
 */
export function ownerChoices(user: Pick<Schema<"UserView">, "phone_number" | "email">): OwnerChoice[] {
  const choices: OwnerChoice[] = [];
  if (user.phone_number) {
    choices.push({ channel: "whatsapp", address: user.phone_number }, { channel: "sms", address: user.phone_number });
  }
  if (user.email) {
    choices.push({ channel: "email", address: user.email });
  }
  return choices;
}

/** The name staff notifications greet the owner by: theirs, else the fallback text. */
export function ownerName(user: Pick<Schema<"UserView">, "display_name">, fallback: string): string {
  const name = user.display_name?.trim();
  return name ? name : fallback;
}

/** Whether this address already receives the business's handoffs. */
export function isAlreadyContact(contacts: readonly ManagerContactView[], choice: OwnerChoice): boolean {
  return contacts.some(
    (contact) =>
      contact.channel === choice.channel && contact.address.toLocaleLowerCase() === choice.address.toLocaleLowerCase(),
  );
}

/** Contacts reached through Telegram (linked with the platform bot). */
export function telegramContacts(contacts: readonly ManagerContactView[]): ManagerContactView[] {
  return contacts.filter((contact) => contact.channel === "telegram");
}

/**
 * A staff Telegram link is waiting to be opened: done once a Telegram
 * contact appears that was not there when the link was made.
 */
export function hasNewTelegramContact(before: readonly ManagerContactView[], now: readonly ManagerContactView[]): boolean {
  const known = new Set(telegramContacts(before).map((contact) => contact.address));
  return telegramContacts(now).some((contact) => !known.has(contact.address));
}
