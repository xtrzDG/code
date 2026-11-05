import type { ReasonMessages } from "@/api/errors";

/**
 * Refusals of a summary channel in the owner's language, by the API's
 * reason codes (`DigestChannelRefusalCode`): Telegram or WhatsApp not set
 * up on the platform, a chat no longer linked, no WhatsApp number.
 */
export const DIGEST_REFUSAL_MESSAGES: ReasonMessages = {
  telegram_not_available: () => ({ key: "digestChannels.refusals.telegramNotAvailable" }),
  telegram_chat_not_linked: () => ({ key: "digestChannels.refusals.telegramChatNotLinked" }),
  whatsapp_not_available: () => ({ key: "digestChannels.refusals.whatsappNotAvailable" }),
  whatsapp_number_missing: () => ({ key: "digestChannels.refusals.whatsappNumberMissing" }),
};
