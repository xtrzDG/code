import "server-only";

import { headers } from "next/headers";

import { unwrap, type ApiResult } from "@/api/result";
import type { CountryListItem, NicheSummaryView, Schema } from "@/api/types";
import type { Locale } from "@/i18n/config";
import { isCountryAvailable } from "@/lib/countries";
import { pickLandingCountry } from "@/lib/landing";
import { getServerApi } from "@/server/api";

export interface LandingData {
  countries: CountryListItem[];
  /** The country whose prices are shown (null: the catalog could not be read). */
  countryCode: string | null;
  plans: Schema<"PlanQuoteList"> | null;
  niches: NicheSummaryView[] | null;
}

/** The data of a public catalog call, or null: the page renders without it. */
async function settle<T>(request: Promise<ApiResult<T>>): Promise<T | null> {
  try {
    return await unwrap(request);
  } catch {
    return null;
  }
}

/** Countries, niches and the plans of one country from the public catalog, in the interface language. */
export async function loadLandingData(requestedCountry: string | undefined, locale: Locale): Promise<LandingData> {
  const [api, headerList] = await Promise.all([getServerApi(), headers()]);
  const [countryList, nicheList] = await Promise.all([
    settle(api.GET("/v1/catalog/countries", { params: { query: { language: locale } } })),
    settle(api.GET("/v1/catalog/niches", { params: { query: { language: locale } } })),
  ]);
  const countries = countryList?.countries ?? [];
  const countryCode = pickLandingCountry({
    requested: requestedCountry,
    available: countries.filter(isCountryAvailable).map((country) => country.country_code),
    // Set by Vercel and Cloudflare when the site runs behind them.
    geoCountry: headerList.get("x-vercel-ip-country") ?? headerList.get("cf-ipcountry"),
    acceptLanguage: headerList.get("accept-language"),
  });
  const plans = countryCode
    ? await settle(api.GET("/v1/catalog/plans", { params: { query: { country_code: countryCode, language: locale } } }))
    : null;
  return { countries, countryCode, plans, niches: nicheList?.niches ?? null };
}
