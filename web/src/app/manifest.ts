import type { MetadataRoute } from "next";

import { getI18n } from "@/i18n/server";
import { HOME_PATH } from "@/lib/navigation";
import { SCHEME_BACKGROUNDS } from "@/lib/theme";
import { getTheme } from "@/server/theme";

/**
 * The web app manifest (/manifest.webmanifest): the cabinet installs as an
 * app that opens on the businesses in a window of its own. Name and
 * language follow the interface language, the colours the theme (both
 * from the cookies); icons are drawn from icon.svg by `npm run gen:icons`.
 */
export default async function manifest(): Promise<MetadataRoute.Manifest> {
  const [{ t, locale }, theme] = await Promise.all([getI18n(), getTheme()]);
  const background = SCHEME_BACKGROUNDS[theme === "light" ? "light" : "dark"];
  return {
    id: "/",
    name: t("common.appName"),
    short_name: t("app.shortName"),
    description: t("common.tagline"),
    lang: locale,
    start_url: HOME_PATH,
    scope: "/",
    display: "standalone",
    background_color: background,
    theme_color: background,
    categories: ["business", "productivity"],
    icons: [
      { src: "/icons/icon-192.png", sizes: "192x192", type: "image/png", purpose: "any" },
      { src: "/icons/icon-512.png", sizes: "512x512", type: "image/png", purpose: "any" },
      { src: "/icons/maskable-192.png", sizes: "192x192", type: "image/png", purpose: "maskable" },
      { src: "/icons/maskable-512.png", sizes: "512x512", type: "image/png", purpose: "maskable" },
    ],
  };
}
