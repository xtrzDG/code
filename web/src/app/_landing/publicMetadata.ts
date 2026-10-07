import "server-only";

import type { Metadata } from "next";
import { headers } from "next/headers";

import type { Locale } from "@/i18n/config";
import { languageAlternates } from "@/lib/publicSite/paths";
import { siteOrigin } from "@/server/siteOrigin";

/** The site's public address for this request (SITE_URL, else the request's own). */
export async function requestSiteOrigin(): Promise<string> {
  return siteOrigin(await headers());
}

/**
 * Metadata of a public page in a language: indexable, its own address as
 * the canonical one, the same page in every language (hreflang) and the
 * Open Graph card. `rest` is the path after the language ("", "/for/hotel").
 */
export async function publicPageMetadata(input: {
  locale: Locale;
  rest: string;
  title: string;
  description: string;
  siteName: string;
}): Promise<Metadata> {
  const origin = await requestSiteOrigin();
  const path = `/${input.locale}${input.rest}`;
  return {
    metadataBase: new URL(origin),
    title: { absolute: input.title },
    description: input.description,
    robots: { index: true, follow: true },
    alternates: { canonical: path, languages: languageAlternates(input.rest) },
    openGraph: {
      type: "website",
      url: path,
      title: input.title,
      description: input.description,
      siteName: input.siteName,
      locale: input.locale,
    },
    twitter: { card: "summary", title: input.title, description: input.description },
  };
}
