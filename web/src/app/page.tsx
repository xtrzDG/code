import type { Metadata } from "next";
import { redirect } from "next/navigation";

import { getI18n } from "@/i18n/server";
import { isCountryAvailable } from "@/lib/countries";
import { sharedTrialDays } from "@/lib/landing";
import { HOME_PATH } from "@/lib/navigation";
import { hasSession } from "@/server/api";

import { Channels } from "./_landing/Channels";
import { Demo } from "./_landing/Demo";
import { Facts } from "./_landing/Facts";
import { Faq } from "./_landing/Faq";
import { Features } from "./_landing/Features";
import { FinalCta } from "./_landing/FinalCta";
import { Hero } from "./_landing/Hero";
import { LandingFooter } from "./_landing/LandingFooter";
import { LandingHeader } from "./_landing/LandingHeader";
import { loadLandingData } from "./_landing/landingData";
import { Niches } from "./_landing/Niches";
import { Pricing } from "./_landing/Pricing";
import { Steps } from "./_landing/Steps";
import { World } from "./_landing/World";

const NO_SCRIPT_STYLE = "[data-reveal]{opacity:1!important;transform:none!important}";

export async function generateMetadata(): Promise<Metadata> {
  const { t, locale } = await getI18n();
  const title = `${t("common.appName")} — ${t("landing.metaTitle")}`;
  const description = t("landing.metaDescription");
  return {
    title: { absolute: title },
    description,
    // The cabinet's pages stay out of search engines; this one is for them.
    robots: { index: true, follow: true },
    openGraph: { type: "website", title, description, siteName: t("common.appName"), locale },
    twitter: { card: "summary", title, description },
  };
}

/**
 * "/": the public page about the product for visitors; signed-in users go
 * straight to their businesses. Rendered on the server from the public
 * catalog (countries, niches, plans of the chosen ?country=).
 */
export default async function RootPage({ searchParams }: PageProps<"/">) {
  if (await hasSession()) {
    redirect(HOME_PATH);
  }
  const query = await searchParams;
  const translator = await getI18n();
  const { t, locale } = translator;
  const data = await loadLandingData(typeof query.country === "string" ? query.country : undefined, locale);
  const supportedCountries = data.countries.filter(isCountryAvailable).length;

  return (
    <div className="relative isolate flex min-h-dvh flex-col">
      {/* Without scripts nothing would reveal itself: show every block as it is. */}
      <noscript>
        <style>{NO_SCRIPT_STYLE}</style>
      </noscript>
      <div aria-hidden className="landing-grain -z-10" />
      <LandingHeader t={t} />
      <main id="main" className="flex-1">
        <Hero t={t} trialDays={data.plans ? sharedTrialDays(data.plans.quotes) : null} />
        <Facts t={t} />
        <Demo t={t} />
        <Steps t={t} />
        <Features t={t} />
        <Channels t={t} />
        <Niches t={t} niches={data.niches} />
        {supportedCountries > 0 ? <World t={t} countryCount={supportedCountries} /> : null}
        <Pricing translator={translator} countries={data.countries} countryCode={data.countryCode} plans={data.plans} />
        <Faq t={t} />
        <FinalCta t={t} />
      </main>
      <LandingFooter t={t} />
    </div>
  );
}
