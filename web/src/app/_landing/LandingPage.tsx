import type { Translator } from "@/i18n/translate";
import { TESTIMONIALS } from "@/content/testimonials";
import { isCountryAvailable } from "@/lib/countries";
import { sharedTrialDays } from "@/lib/landing";
import { localeHomePath } from "@/lib/publicSite/paths";
import { billed } from "@/lib/publicSite/prices";
import { absoluteUrl, faqJsonLd, organizationJsonLd, schemaPrice, softwareJsonLd } from "@/lib/publicSite/seo";
import { testimonialsFor } from "@/lib/publicSite/testimonials";
import { currencyFractionDigits } from "@/lib/format";

import { Channels } from "./Channels";
import { Demo } from "./Demo";
import { Facts } from "./Facts";
import { FAQ_QUESTIONS, Faq } from "./Faq";
import { Features } from "./Features";
import { FinalCta } from "./FinalCta";
import { Hero } from "./Hero";
import { JsonLd } from "./JsonLd";
import { LandingFooter } from "./LandingFooter";
import { LandingHeader } from "./LandingHeader";
import type { LandingData } from "./landingData";
import { Niches } from "./Niches";
import { Pricing } from "./Pricing";
import { Roi } from "./Roi";
import { SetupOptions } from "./SetupOptions";
import { Steps } from "./Steps";
import { Testimonials } from "./Testimonials";
import { World } from "./World";

const NO_SCRIPT_STYLE = "[data-reveal]{opacity:1!important;transform:none!important}";

/** The structured data of the landing page: who offers it, what it costs, the questions. */
function landingJsonLd(translator: Translator, data: LandingData, origin: string) {
  const { t, locale } = translator;
  const name = t("common.appName");
  const url = absoluteUrl(origin, localeHomePath(locale));
  const offers = (data.plans?.quotes ?? []).map((quote) => {
    const money = billed(quote.local_monthly_price, quote.monthly_price).money;
    return {
      name: quote.name,
      price: schemaPrice(money.amount_minor, currencyFractionDigits(money.currency_code)),
      currency: money.currency_code,
    };
  });
  return [
    organizationJsonLd({ name, url: absoluteUrl(origin, "/"), logo: absoluteUrl(origin, "/icon.svg") }),
    softwareJsonLd({ name, description: t("landing.metaDescription"), url, language: locale, offers }),
    faqJsonLd(FAQ_QUESTIONS.map(([question, answer]) => ({ question: t(question), answer: t(answer) }))),
  ];
}

/**
 * The public page about the product in one language (/en, /ru, /ka): a
 * live demo assistant, what it does, the kinds of business, the value
 * calculator, honest prices of the chosen country (?country=), the two
 * ways to set it up, owners' words and the questions.
 */
export function LandingPage({
  translator,
  data,
  origin,
}: {
  translator: Translator;
  data: LandingData;
  origin: string;
}) {
  const { t, locale } = translator;
  const supportedCountries = data.countries.filter(isCountryAvailable).length;
  const quotes = data.plans?.quotes ?? null;
  const hasLiveDemo = (data.demos?.demos.length ?? 0) > 0;

  return (
    <div className="relative isolate flex min-h-dvh flex-col">
      {/* Without scripts nothing would reveal itself: show every block as it is. */}
      <noscript>
        <style>{NO_SCRIPT_STYLE}</style>
      </noscript>
      <JsonLd data={landingJsonLd(translator, data, origin)} />
      <div aria-hidden className="landing-grain -z-10" />
      <LandingHeader t={t} />
      <main id="main" className="flex-1">
        <Hero t={t} trialDays={quotes ? sharedTrialDays(quotes) : null} demos={data.demos} />
        <Facts t={t} />
        {/* The hero shows this example itself when no live demo answers. */}
        {hasLiveDemo ? <Demo t={t} /> : null}
        <Steps t={t} />
        <Features t={t} />
        <Channels t={t} />
        <Niches t={t} niches={data.niches} locale={locale} />
        <Roi t={t} niches={data.niches} quotes={quotes} />
        {supportedCountries > 0 ? <World t={t} countryCount={supportedCountries} /> : null}
        <Pricing
          translator={translator}
          countries={data.countries}
          countryCode={data.countryCode}
          plans={data.plans}
          formAction={localeHomePath(locale)}
        />
        <SetupOptions translator={translator} quote={quotes?.[0] ?? null} />
        <Testimonials t={t} items={testimonialsFor(TESTIMONIALS, locale)} />
        <Faq t={t} />
        <FinalCta t={t} />
      </main>
      <LandingFooter t={t} locale={locale} niches={data.niches} />
    </div>
  );
}
