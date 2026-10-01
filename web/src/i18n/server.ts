import "server-only";

import { cookies, headers } from "next/headers";

import { LOCALE_COOKIE, resolveLocale, type Locale } from "./config";
import { FALLBACK_MESSAGES, getMessages } from "./messages";
import { createTranslator, type MessageTree, type Translator } from "./translate";

/** The interface language of the current request (Server Components, route handlers). */
export async function getLocale(): Promise<Locale> {
  const [cookieStore, headerList] = await Promise.all([cookies(), headers()]);
  return resolveLocale({
    cookieValue: cookieStore.get(LOCALE_COOKIE)?.value,
    acceptLanguage: headerList.get("accept-language"),
  });
}

/**
 * Translator for Server Components:
 *
 *     const { t } = await getI18n();
 *     return <h1>{t("businesses.title")}</h1>;
 */
export async function getI18n(): Promise<Translator & { messages: MessageTree }> {
  const locale = await getLocale();
  const messages = getMessages(locale);
  return { ...createTranslator(locale, messages, FALLBACK_MESSAGES), messages };
}
