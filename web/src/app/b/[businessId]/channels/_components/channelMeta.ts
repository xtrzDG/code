import type { ComponentType } from "react";

import {
  IconInstagram,
  IconMessenger,
  IconPhone,
  IconSend,
  IconWhatsApp,
  IconWindow,
  type IconProps,
} from "@/components/workspace/icons";
import type { MessageKey } from "@/i18n/translate";

import type { ChannelState, ConnectField, ConnectFieldError, ConnectableChannel } from "../_lib/channels";

export { CHANNEL_NAMES } from "@/components/workspace/channelNames";

export const CHANNEL_ICONS: Record<ConnectableChannel, ComponentType<IconProps>> = {
  web_chat: IconWindow,
  telegram: IconSend,
  whatsapp: IconWhatsApp,
  instagram: IconInstagram,
  messenger: IconMessenger,
  phone: IconPhone,
};

export const CHANNEL_BLURBS: Record<ConnectableChannel, MessageKey> = {
  web_chat: "channels.blurbs.web_chat",
  telegram: "channels.blurbs.telegram",
  whatsapp: "channels.blurbs.whatsapp",
  instagram: "channels.blurbs.instagram",
  messenger: "channels.blurbs.messenger",
  phone: "channels.blurbs.phone",
};

export const CHANNEL_ACCOUNT_LABELS: Partial<Record<ConnectableChannel, MessageKey>> = {
  telegram: "channels.account.telegram",
  whatsapp: "channels.account.whatsapp",
  instagram: "channels.account.instagram",
  messenger: "channels.account.messenger",
  phone: "channels.account.phone",
};

export const CHANNEL_STATE_LABELS: Record<ChannelState, MessageKey> = {
  not_connected: "channels.state.not_connected",
  pending: "channels.state.pending",
  connected: "channels.state.connected",
  disabled: "channels.state.disabled",
  error: "channels.state.error",
};

/** The three "how to connect" steps of each channel that has a form. */
export const CHANNEL_STEPS: Partial<Record<ConnectableChannel, readonly MessageKey[]>> = {
  telegram: ["channels.steps.telegram.step1", "channels.steps.telegram.step2", "channels.steps.telegram.step3"],
  whatsapp: ["channels.steps.whatsapp.step1", "channels.steps.whatsapp.step2", "channels.steps.whatsapp.step3"],
  instagram: ["channels.steps.instagram.step1", "channels.steps.instagram.step2", "channels.steps.instagram.step3"],
  messenger: ["channels.steps.messenger.step1", "channels.steps.messenger.step2", "channels.steps.messenger.step3"],
  phone: ["channels.steps.phone.step1", "channels.steps.phone.step2", "channels.steps.phone.step3"],
};

export const FIELD_LABELS: Record<ConnectField, { label: MessageKey; hint: MessageKey }> = {
  botToken: { label: "channels.fields.botToken", hint: "channels.fields.botTokenHint" },
  phoneNumberId: { label: "channels.fields.phoneNumberId", hint: "channels.fields.phoneNumberIdHint" },
  businessAccountId: { label: "channels.fields.businessAccountId", hint: "channels.fields.businessAccountIdHint" },
  pageId: { label: "channels.fields.pageId", hint: "channels.fields.pageIdHint" },
  pageAccessToken: { label: "channels.fields.pageAccessToken", hint: "channels.fields.pageAccessTokenHint" },
  phoneNumber: { label: "channels.fields.phoneNumber", hint: "channels.fields.phoneNumberHint" },
  countryHint: { label: "channels.fields.countryHint", hint: "channels.fields.countryHintHint" },
};

export const FIELD_ERRORS: Record<ConnectFieldError, MessageKey> = {
  required: "channels.fieldErrors.required",
  botToken: "channels.fieldErrors.botToken",
  digits: "channels.fieldErrors.digits",
  pageToken: "channels.fieldErrors.pageToken",
};
