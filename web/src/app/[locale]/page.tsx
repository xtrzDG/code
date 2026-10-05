import type { Metadata } from "next";
import { notFound } from "next/navigation";

import { isLocale } from "@/i18n/config";
import { getI18n } from "@/i18n/server";

import { LandingPage } from "../_landing/LandingPage";
import { loadLandingData } from "../_landing/landingData";
import { publicPageMetadata, requestSiteOrigin } from "../_landing/publicMetadata";

export async function generateMetadata({ params }: PageProps<"/[locale]">): Promise<Metadata> {
  const { locale } = await params;
  if (!isLocale(locale)) {
    return {};
  }
  const { t } = await getI18n();
  return publicPageMetadata({
    locale,
    rest: "",
    title: `${t("common.appName")} — ${t("landing.metaTitle")}`,
    description: t("landing.metaDescription"),
    siteName: t("common.appName"),
  });
}

/**
 * "/en", "/ru", "/ka": the public page about the product in that language,
 * for visitors and search engines alike (a signed-in owner may read it
 * too). Rendered on the server from the public catalog (countries, niches,
 * the plans of the chosen ?country=, the sandbox demos).
 */
export default async function LocaleLandingPage({ params, searchParams }: PageProps<"/[locale]">) {
  const [{ locale }, query] = await Promise.all([params, searchParams]);
  if (!isLocale(locale)) {
    notFound();
  }
  const translator = await getI18n();
  const [data, origin] = await Promise.all([
    loadLandingData(typeof query.country === "string" ? query.country : undefined, locale),
    requestSiteOrigin(),
  ]);
  return <LandingPage translator={translator} data={data} origin={origin} />;
}
