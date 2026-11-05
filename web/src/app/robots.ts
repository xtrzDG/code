import type { MetadataRoute } from "next";
import { headers } from "next/headers";

import { siteOrigin } from "@/server/siteOrigin";

/**
 * Only the public site is for search engines (/, /en, /ru/for/hotel, the
 * legal pages); the cabinet is private. The sitemap lists the public pages.
 */
export default async function robots(): Promise<MetadataRoute.Robots> {
  const origin = siteOrigin(await headers());
  return {
    rules: {
      userAgent: "*",
      allow: "/",
      disallow: ["/b/", "/businesses", "/admin", "/login", "/api/", "/integrations/", "/create", "/account", "/c/", "/n/"],
    },
    sitemap: `${origin}/sitemap.xml`,
  };
}
