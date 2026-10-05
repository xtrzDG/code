import "server-only";

import { cookies, headers } from "next/headers";

import { PATH_LOCALE_HEADER } from "@/lib/publicSite/paths";

import { LOCALE_COOKIE, matchLocale, resolveLocale, type Locale } from "./config";
import { FALLBACK_MESSAGES, getMessages } from "./messages";
import { pseudoMessages, wantsPseudoLocale } from "./pseudo";
import { createTranslator, type MessageTree, type Translator } from "./translate";

let pseudoDictionary: MessageTree | undefined;

/**
 * The interface language of the current request (Server Components, route
 * handlers). A public page's own language (/ka, /ru/for/hotel, set by the
 * proxy from the path) comes first; then the cookie, Accept-Language and
 * English.
 */
export async function getLocale(): Promise<Locale> {
  const [cookieStore, headerList] = await Promise.all([cookies(), headers()]);
  const pathLocale = matchLocale(headerList.get(PATH_LOCALE_HEADER));
  if (pathLocale) {
    return pathLocale;
  }
  return resolveLocale({
    cookieValue: cookieStore.get(LOCALE_COOKIE)?.value,
    acceptLanguage: headerList.get("accept-language"),
  });
}

/**
 * The texts of the current request: its language's dictionary, or the
 * pseudo-locale when the server allows it and the cookie asks for it
 * (English dates and numbers, stretched accented texts; see ./pseudo.ts).
 */
async function getRequestMessages(locale: Locale): Promise<MessageTree> {
  const cookieStore = await cookies();
  if (wantsPseudoLocale(cookieStore.get(LOCALE_COOKIE)?.value)) {
    pseudoDictionary ??= pseudoMessages(getMessages("en"));
    return pseudoDictionary;
  }
  return getMessages(locale);
}

/**
 * Translator for Server Components:
 *
 *     const { t } = await getI18n();
 *     return <h1>{t("businesses.title")}</h1>;
 */
export async function getI18n(): Promise<Translator & { messages: MessageTree }> {
  const locale = await getLocale();
  const messages = await getRequestMessages(locale);
  return { ...createTranslator(locale, messages, FALLBACK_MESSAGES), messages };
}
