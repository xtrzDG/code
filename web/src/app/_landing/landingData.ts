import "server-only";

import { headers } from "next/headers";

import type { CountryListItem, NicheSummaryView, Schema } from "@/api/types";
import type { Locale } from "@/i18n/config";
import { isCountryAvailable } from "@/lib/countries";
import { pickLandingCountry } from "@/lib/landing";
import { getServerApi } from "@/server/api";
import { settlePublic } from "@/server/publicData";

export interface LandingData {
  countries: CountryListItem[];
  /** The country whose prices are shown (null: the catalog could not be read). */
  countryCode: string | null;
  plans: Schema<"PlanQuoteList"> | null;
  niches: NicheSummaryView[] | null;
  /** The sandbox demos of the hero (null: none answers right now). */
  demos: Schema<"PublicDemoList"> | null;
}

/**
 * The country whose prices a public page shows: the one asked for
 * (?country=), else a guess among the countries with their own price book
 * (the visitor's country by the hosting proxy, else by the browser's
 * languages), so a first look never lands on mere conversions.
 */
async function pickPricedCountry(
  countries: readonly CountryListItem[],
  requestedCountry: string | undefined,
): Promise<string | null> {
  const headerList = await headers();
  const available = countries.filter(isCountryAvailable);
  return pickLandingCountry({
    requested: requestedCountry,
    available: available.map((country) => country.country_code),
    priced: available.filter((country) => country.has_price_book).map((country) => country.country_code),
    // Set by Vercel and Cloudflare when the site runs behind them.
    geoCountry: headerList.get("x-vercel-ip-country") ?? headerList.get("cf-ipcountry"),
    acceptLanguage: headerList.get("accept-language"),
  });
}

/** Countries, niches, demos and the plans of one country from the public catalog, in the page's language. */
export async function loadLandingData(requestedCountry: string | undefined, locale: Locale): Promise<LandingData> {
  const api = await getServerApi();
  const [countryList, nicheList, demos] = await Promise.all([
    settlePublic(api.GET("/v1/catalog/countries", { params: { query: { language: locale } } })),
    settlePublic(api.GET("/v1/catalog/niches", { params: { query: { language: locale } } })),
    settlePublic(api.GET("/v1/public-demos", { params: { query: { language: locale } } })),
  ]);
  const countries = countryList?.countries ?? [];
  const countryCode = await pickPricedCountry(countries, requestedCountry);
  const plans = countryCode
    ? await settlePublic(api.GET("/v1/catalog/plans", { params: { query: { country_code: countryCode, language: locale } } }))
    : null;
  return { countries, countryCode, plans, niches: nicheList?.niches ?? null, demos };
}
