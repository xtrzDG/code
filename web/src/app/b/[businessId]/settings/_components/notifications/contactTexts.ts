/** Texts of the Notifications tab: channels, address labels and hints, and errors. */

import type { ErrorMessageOverrides } from "@/api/errors";
import type { MessageKey } from "@/i18n/translate";

import type { ContactError, ManagerContactChannel } from "../../_lib/contacts";

export const CHANNELS: readonly ManagerContactChannel[] = ["telegram", "whatsapp", "email", "sms"];

export const CHANNEL_LABELS: Record<ManagerContactChannel, MessageKey> = {
  telegram: "settings.contacts.channels.telegram",
  whatsapp: "settings.contacts.channels.whatsapp",
  email: "settings.contacts.channels.email",
  sms: "settings.contacts.channels.sms",
};

export const ADDRESS_LABELS: Record<ManagerContactChannel, MessageKey> = {
  telegram: "settings.contacts.address.telegram",
  whatsapp: "settings.contacts.address.whatsapp",
  email: "settings.contacts.address.email",
  sms: "settings.contacts.address.sms",
};

export const ADDRESS_HINTS: Record<ManagerContactChannel, MessageKey> = {
  telegram: "settings.contacts.addressHint.telegram",
  whatsapp: "settings.contacts.addressHint.whatsapp",
  email: "settings.contacts.addressHint.email",
  sms: "settings.contacts.addressHint.sms",
};

export const CONTACT_ERRORS: Record<ContactError, MessageKey> = {
  required: "settings.contacts.errors.required",
  tooLong: "settings.contacts.errors.tooLong",
  email: "settings.contacts.errors.email",
  chatId: "settings.contacts.errors.chatId",
  duplicate: "settings.contacts.errors.duplicate",
};

/** The only 409 of a contacts save: the list was saved by someone else after it was shown. */
export const STALE_LIST_MESSAGES: ErrorMessageOverrides = { conflict: "settings.contacts.stale" };
