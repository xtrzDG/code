import "server-only";

import { cookies, headers } from "next/headers";

import { PATH_LOCALE_HEADER } from "@/lib/publicSite/paths";

import { LOCALE_COOKIE, localeDirection, matchLocale, resolveLocale, type Locale, type LocaleDirection } from "./config";
import { FALLBACK_MESSAGES, getMessages } from "./messages";
import { pseudoLocaleDirection, pseudoMessages } from "./pseudo";
import { publicClientMessages, type TextScope } from "./publicScope";
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
 * The texts of the current request and the direction its pages read in: its
 * language's dictionary, or the pseudo-locale when the server allows it and
 * the cookie asks for it (English dates and numbers, stretched accented
 * texts, left to right or right to left; see ./pseudo.ts).
 */
async function getRequestTexts(locale: Locale): Promise<{ messages: MessageTree; direction: LocaleDirection }> {
  const cookieStore = await cookies();
  const pseudoDirection = pseudoLocaleDirection(cookieStore.get(LOCALE_COOKIE)?.value);
  if (pseudoDirection) {
    pseudoDictionary ??= pseudoMessages(getMessages("en"));
    return { messages: pseudoDictionary, direction: pseudoDirection };
  }
  return { messages: getMessages(locale), direction: localeDirection(locale) };
}

/**
 * Translator for Server Components:
 *
 *     const { t } = await getI18n();
 *     return <h1>{t("businesses.title")}</h1>;
 */
export async function getI18n(): Promise<Translator & { messages: MessageTree; direction: LocaleDirection }> {
  const locale = await getLocale();
  const { messages, direction } = await getRequestTexts(locale);
  return { ...createTranslator(locale, messages, FALLBACK_MESSAGES), messages, direction };
}

/**
 * What the browser gets of the dictionary: the public site's pages (the
 * proxy marks them with their path's language) only the texts of their
 * client components (./publicScope.ts), every other page all of it.
 */
export async function getClientTexts(messages: MessageTree): Promise<{ messages: MessageTree; scope: TextScope }> {
  const headerList = await headers();
  return matchLocale(headerList.get(PATH_LOCALE_HEADER))
    ? { messages: publicClientMessages(messages), scope: "public" }
    : { messages, scope: "full" };
}
