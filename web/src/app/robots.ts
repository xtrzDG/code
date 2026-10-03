import type { MetadataRoute } from "next";

/** Only the public landing page is for search engines; the cabinet is private. */
export default function robots(): MetadataRoute.Robots {
  return {
    rules: {
      userAgent: "*",
      allow: "/",
      disallow: ["/b/", "/businesses", "/admin", "/login", "/api/", "/integrations/"],
    },
  };
}
