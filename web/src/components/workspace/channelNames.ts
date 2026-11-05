import type { Schema } from "@/api/types";
import type { MessageKey } from "@/i18n/translate";

/** Names of the customer channels (channels, billing and admin pages). */
export const CHANNEL_NAMES: Record<Schema<"ChannelKind">, MessageKey> = {
  phone: "channels.kinds.phone",
  whatsapp: "channels.kinds.whatsapp",
  instagram: "channels.kinds.instagram",
  messenger: "channels.kinds.messenger",
  telegram: "channels.kinds.telegram",
  web_chat: "channels.kinds.web_chat",
  viber: "channels.kinds.viber",
  owner_test: "channels.kinds.owner_test",
};
