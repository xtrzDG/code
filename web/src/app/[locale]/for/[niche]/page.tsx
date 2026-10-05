import type { Metadata } from "next";
import { notFound } from "next/navigation";

import type { NicheSummaryView } from "@/api/types";
import { TESTIMONIALS } from "@/content/testimonials";
import { isLocale, type Locale } from "@/i18n/config";
import { getI18n } from "@/i18n/server";
import { localeHomePath, nichePath } from "@/lib/publicSite/paths";
import { absoluteUrl, serviceJsonLd } from "@/lib/publicSite/seo";
import { testimonialsFor } from "@/lib/publicSite/testimonials";
import { getServerApi } from "@/server/api";
import { settlePublic } from "@/server/publicData";

import { JsonLd } from "../../../_landing/JsonLd";
import { LandingFooter } from "../../../_landing/LandingFooter";
import { LandingHeader } from "../../../_landing/LandingHeader";
import { loadLandingData } from "../../../_landing/landingData";
import { NicheAbilities } from "../../../_landing/niche/NicheAbilities";
import { NicheDemo } from "../../../_landing/niche/NicheDemo";
import { NicheHero } from "../../../_landing/niche/NicheHero";
import { OtherNiches } from "../../../_landing/niche/OtherNiches";
import { Pricing } from "../../../_landing/Pricing";
import { publicPageMetadata, requestSiteOrigin } from "../../../_landing/publicMetadata";
import { Roi } from "../../../_landing/Roi";
import { Testimonials } from "../../../_landing/Testimonials";

/** One kind of business from the public catalog in the page's language, or null. */
async function loadNiche(locale: Locale, key: string): Promise<NicheSummaryView | null> {
  const api = await getServerApi();
  const details = await settlePublic(
    api.GET("/v1/catalog/niches/{niche_key}", { params: { path: { niche_key: key }, query: { language: locale } } }),
  );
  return details?.niche ?? null;
}

export async function generateMetadata({ params }: PageProps<"/[locale]/for/[niche]">): Promise<Metadata> {
  const { locale, niche: key } = await params;
  if (!isLocale(locale)) {
    return {};
  }
  const [{ t }, niche] = await Promise.all([getI18n(), loadNiche(locale, key)]);
  if (!niche) {
    return { title: t("nichePage.notFound"), robots: { index: false, follow: true } };
  }
  return publicPageMetadata({
    locale,
    rest: `/for/${encodeURIComponent(niche.key)}`,
    title: `${t("nichePage.metaTitle", { niche: niche.name })} · ${t("common.appName")}`,
    description: t("nichePage.metaDescription", { description: niche.description }),
    siteName: t("common.appName"),
  });
}

/**
 * "/ru/for/restaurant": the public page of one kind of business, generated
 * from the niche catalog: what the assistant does for it, a demo business
 * of this kind to talk to (when one is configured), the value calculator
 * with its typical check, honest prices and the other kinds of business.
 */
export default async function NichePage({ params, searchParams }: PageProps<"/[locale]/for/[niche]">) {
  const [{ locale, niche: key }, query] = await Promise.all([params, searchParams]);
  if (!isLocale(locale)) {
    notFound();
  }
  const translator = await getI18n();
  const { t } = translator;
  const [data, niche, origin] = await Promise.all([
    loadLandingData(typeof query.country === "string" ? query.country : undefined, locale),
    loadNiche(locale, key),
    requestSiteOrigin(),
  ]);
  if (!niche) {
    notFound();
  }
  const home = localeHomePath(locale);
  const demo = data.demos?.demos.find((candidate) => candidate.niche_key === niche.key) ?? null;
  const quotes = data.plans?.quotes ?? null;
  const path = nichePath(locale, niche.key);

  return (
    <div className="relative isolate flex min-h-dvh flex-col">
      <JsonLd
        data={serviceJsonLd({
          name: t("nichePage.metaTitle", { niche: niche.name }),
          description: niche.description,
          url: absoluteUrl(origin, path),
          language: locale,
          audience: niche.name,
          provider: t("common.appName"),
        })}
      />
      <div aria-hidden className="landing-grain -z-10" />
      <LandingHeader t={t} home={home} />
      <main id="main" className="flex-1" data-niche={niche.key}>
        <NicheHero t={t} niche={niche} home={home} hasDemo={demo !== null} />
        {demo && data.demos ? <NicheDemo t={t} demo={demo} messagesPerHour={data.demos.messages_per_hour} /> : null}
        <NicheAbilities t={t} locale={locale} niche={niche} quotes={quotes} />
        <Roi
          t={t}
          niches={data.niches ?? [niche]}
          quotes={quotes}
          initialNicheKey={niche.key}
          recommendedPlans={niche.recommended_plans}
        />
        <Pricing
          translator={translator}
          countries={data.countries}
          countryCode={data.countryCode}
          plans={data.plans}
          formAction={path}
        />
        <Testimonials t={t} items={testimonialsFor(TESTIMONIALS, locale, niche.key)} />
        <OtherNiches t={t} locale={locale} niches={data.niches ?? []} current={niche.key} />
      </main>
      <LandingFooter t={t} locale={locale} home={home} niches={data.niches} />
    </div>
  );
}
