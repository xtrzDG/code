/**
 * Addresses of the public site: every public page lives under its
 * language (`/ka`, `/ru/for/restaurant`, `/en/privacy`), so search engines
 * index each language on its own URL and link them with hreflang. The
 * cabinet's routes (/login, /b/…, /businesses, …) stay where they are.
 */

import { LOCALES, isLocale, type Locale } from "@/i18n/config";

/** Request header the proxy sets from the path's language (never from the browser). */
export const PATH_LOCALE_HEADER = "x-aw-path-locale";

/** The public legal and contact pages, in the order the footer lists them. */
export const LEGAL_PAGES = ["terms", "privacy", "dpa", "security", "contact"] as const;

export type LegalPage = (typeof LEGAL_PAGES)[number];

export function isLegalPage(value: string): value is LegalPage {
  return (LEGAL_PAGES as readonly string[]).includes(value);
}

/** The public home of a language: "/ru". */
export function localeHomePath(locale: Locale): string {
  return `/${locale}`;
}

/** A niche's page: "/ka/for/restaurant". */
export function nichePath(locale: Locale, nicheKey: string): string {
  return `/${locale}/for/${encodeURIComponent(nicheKey)}`;
}

/** A legal or contact page: "/en/privacy". */
export function legalPath(locale: Locale, page: LegalPage): string {
  return `/${locale}/${page}`;
}

/** The language a public path is in ("/ru/for/hotel" -> "ru"), or null. */
export function pathLocale(pathname: string): Locale | null {
  const first = pathname.split("/")[1] ?? "";
  return isLocale(first) ? first : null;
}

/**
 * The same public page in another language: "/ru/for/hotel" -> "/ka/for/hotel".
 * A path without a language is returned unchanged.
 */
export function switchPathLocale(pathname: string, locale: Locale): string {
  const current = pathLocale(pathname);
  if (current === null) {
    return pathname;
  }
  return `/${locale}${pathname.slice(current.length + 1)}`;
}

/**
 * Where a page without a language goes: "/privacy" -> "/ru/privacy" for a
 * Russian reader. Null for any other path.
 */
export function localizedRedirectPath(pathname: string, locale: Locale): string | null {
  const page = pathname.replace(/^\/+|\/+$/g, "");
  return isLegalPage(page) ? legalPath(locale, page) : null;
}

/**
 * hreflang alternates of a page given by its path after the language
 * ("" for the home, "/for/hotel", "/privacy"): every language plus
 * x-default, the address that picks the reader's language.
 */
export function languageAlternates(rest: string): Record<string, string> {
  const alternates: Record<string, string> = {};
  for (const locale of LOCALES) {
    alternates[locale] = `/${locale}${rest}`;
  }
  alternates["x-default"] = rest === "" ? "/" : `/${LOCALES[LOCALES.length - 1]}${rest}`;
  return alternates;
}

/**
 * Integrations the platform connects today. The niche catalog also names
 * systems planned for a kind of business; a public page names only these.
 */
const LIVE_INTEGRATIONS: readonly string[] = ["Google Calendar"];

export function liveIntegrations(names: readonly string[] | undefined): string[] {
  return (names ?? []).filter((name) => LIVE_INTEGRATIONS.includes(name));
}
