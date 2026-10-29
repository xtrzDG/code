import type { MetadataRoute } from "next";
import { headers } from "next/headers";

import { publicPageRests, sitemapEntries } from "@/lib/publicSite/sitemap";
import { getServerApi } from "@/server/api";
import { settlePublic } from "@/server/publicData";
import { siteOrigin } from "@/server/siteOrigin";

/**
 * /sitemap.xml: the public pages in every language with their hreflang
 * alternates; the kinds of business come from the niche catalog, the
 * legal pages once the texts are final (LEGAL_TEXTS_FINAL).
 */
export default async function sitemap(): Promise<MetadataRoute.Sitemap> {
  const [api, requestHeaders] = await Promise.all([getServerApi(), headers()]);
  const [niches, overview] = await Promise.all([
    settlePublic(api.GET("/v1/catalog/niches", { params: { query: { language: "en" } } })),
    settlePublic(api.GET("/v1/legal/overview")),
  ]);
  const rests = publicPageRests(
    (niches?.niches ?? []).map((niche) => niche.key),
    overview ? !overview.is_draft : false,
  );
  return sitemapEntries(siteOrigin(requestHeaders), rests);
}
