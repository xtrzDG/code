/**
 * The guided Telegram connection: a bot is made in Telegram by @BotFather
 * (/newbot, a name, a username ending in "bot"), which then sends a token.
 * The page suggests the username from the business name and checks a
 * pasted token with the API (which bot it opens) before connecting it.
 */

import type { ApiError } from "@/api/errors";
import type { Schema } from "@/api/types";

export type TelegramBotCheck = Schema<"TelegramBotCheckView">;

export const BOTFATHER_URL = "https://t.me/BotFather";
export const NEW_BOT_COMMAND = "/newbot";

/** Telegram usernames: 5 to 32 of a-z, 0-9 and "_", starting with a letter; a bot's ends in "bot". */
const MAX_USERNAME_LENGTH = 32;
const BOT_SUFFIX = "_bot";
const FALLBACK_BASE = "my_assistant";
const MIN_BASE_LENGTH = 3;

const GEORGIAN: Readonly<Record<string, string>> = {
  ა: "a", ბ: "b", გ: "g", დ: "d", ე: "e", ვ: "v", ზ: "z", თ: "t", ი: "i", კ: "k", ლ: "l", მ: "m", ნ: "n",
  ო: "o", პ: "p", ჟ: "zh", რ: "r", ს: "s", ტ: "t", უ: "u", ფ: "p", ქ: "k", ღ: "gh", ყ: "q", შ: "sh", ჩ: "ch",
  ც: "ts", ძ: "dz", წ: "ts", ჭ: "ch", ხ: "kh", ჯ: "j", ჰ: "h",
};

const CYRILLIC: Readonly<Record<string, string>> = {
  а: "a", б: "b", в: "v", г: "g", д: "d", е: "e", ё: "e", ж: "zh", з: "z", и: "i", й: "y", к: "k", л: "l",
  м: "m", н: "n", о: "o", п: "p", р: "r", с: "s", т: "t", у: "u", ф: "f", х: "kh", ц: "ts", ч: "ch", ш: "sh",
  щ: "shch", ъ: "", ы: "y", ь: "", э: "e", ю: "yu", я: "ya", і: "i", ї: "yi", є: "ye", ґ: "g",
};

/** Latin letters for a name in Georgian, Cyrillic or accented Latin: "Мцване Эзо" -> "mtsvane ezo". */
export function transliterate(text: string): string {
  return [...text.toLowerCase()]
    .map((letter) => GEORGIAN[letter] ?? CYRILLIC[letter] ?? letter)
    .join("")
    .normalize("NFKD")
    .replace(/[̀-ͯ]/g, "");
}

function usernameBase(businessName: string): string {
  const base = transliterate(businessName)
    .replace(/[^a-z0-9]+/g, "_")
    .replace(/^[^a-z]+/, "")
    .replace(/_+$/, "")
    .replace(/_bot$|bot$/, "")
    .replace(/_+$/, "");
  const fitting = base.slice(0, MAX_USERNAME_LENGTH - BOT_SUFFIX.length - 1).replace(/_+$/, "");
  return fitting.length >= MIN_BASE_LENGTH ? fitting : FALLBACK_BASE;
}

/** The username to give @BotFather: "Mtsvane Ezo" -> "mtsvane_ezo_bot". */
export function suggestBotUsername(businessName: string): string {
  return `${usernameBase(businessName)}${BOT_SUFFIX}`;
}

/** Another one when the first is taken: "mtsvane_ezo2_bot". */
export function alternativeBotUsername(businessName: string): string {
  return `${usernameBase(businessName)}2${BOT_SUFFIX}`;
}

/** A pasted token without the spaces and line breaks a copy may bring along. */
export function cleanBotToken(text: string): string {
  return text.replace(/\s+/g, "");
}

/** Why a token check failed: not a token at all, a token Telegram does not know, or no answer now. */
export type TokenCheckProblem = "format" | "rejected" | "unavailable";

export function tokenCheckProblem(error: ApiError): TokenCheckProblem {
  const codes = error.reasons.map((reason) => reason.code);
  if (codes.includes("telegram_token_format")) {
    return "format";
  }
  return codes.includes("telegram_token_rejected") ? "rejected" : "unavailable";
}

/** "@mtsvane_ezo_bot" */
export function botHandle(check: Pick<TelegramBotCheck, "username">): string {
  return check.username.startsWith("@") ? check.username : `@${check.username}`;
}

/** The letter shown when the bot has no photo. */
export function botInitial(check: Pick<TelegramBotCheck, "username" | "display_name">): string {
  const source = (check.display_name ?? "").trim() || check.username.replace(/^@/, "");
  const first = [...source][0] ?? "?";
  // Georgian (Mkhedruli) has no capitals: uppercasing would turn it into Mtavruli.
  return /^[\u10D0-\u10FF]/.test(first) ? first : first.toLocaleUpperCase();
}
