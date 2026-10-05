/**
 * The sitemap of the public site: every public page in every language,
 * each with its alternates in the other languages (hreflang), so search
 * engines find and pair them.
 */

import { LOCALES } from "@/i18n/config";

import { LEGAL_PAGES } from "./paths";
import { absoluteUrl } from "./seo";

export interface SitemapEntry {
  url: string;
  changeFrequency: "weekly" | "monthly";
  priority: number;
  alternates: { languages: Record<string, string> };
}

/**
 * The paths after the language of the public pages: the home, each kind of
 * business, and the legal and contact pages once they are final (drafts
 * are not offered to search engines).
 */
export function publicPageRests(nicheKeys: readonly string[], legalTextsFinal: boolean): string[] {
  return [
    "",
    ...nicheKeys.map((key) => `/for/${encodeURIComponent(key)}`),
    ...(legalTextsFinal ? LEGAL_PAGES.map((page) => `/${page}`) : []),
  ];
}

export function sitemapEntries(origin: string, rests: readonly string[]): SitemapEntry[] {
  return rests.flatMap((rest) => {
    const languages = Object.fromEntries(LOCALES.map((locale) => [locale, absoluteUrl(origin, `/${locale}${rest}`)]));
    return LOCALES.map((locale) => ({
      url: absoluteUrl(origin, `/${locale}${rest}`),
      changeFrequency: rest.startsWith("/for/") || rest === "" ? ("weekly" as const) : ("monthly" as const),
      priority: rest === "" ? 1 : rest.startsWith("/for/") ? 0.8 : 0.3,
      alternates: { languages },
    }));
  });
}
