/**
 * Texts of the public site around the cabinet: the landing page's live
 * demo and value calculator, the pages of each kind of business, the
 * legal and contact pages and the honest price notes.
 *
 * Top-level keys are namespaces; they are spread into en.ts, ru.ts and
 * ka.ts. `ru` and `ka` are type-checked against `en`.
 */

import type { Translation } from "../../translate";
import { legalPagesEn } from "./site/legalPages.en";
import { legalPagesKa } from "./site/legalPages.ka";
import { legalPagesRu } from "./site/legalPages.ru";
import { nichePageEn } from "./site/nichePage.en";
import { nichePageKa } from "./site/nichePage.ka";
import { nichePageRu } from "./site/nichePage.ru";
import { publicDemoEn } from "./site/publicDemo.en";
import { publicDemoKa } from "./site/publicDemo.ka";
import { publicDemoRu } from "./site/publicDemo.ru";
import { publicPricingEn } from "./site/publicPricing.en";
import { publicPricingKa } from "./site/publicPricing.ka";
import { publicPricingRu } from "./site/publicPricing.ru";
import { roiEn } from "./site/roi.en";
import { roiKa } from "./site/roi.ka";
import { roiRu } from "./site/roi.ru";
import { legalPagesHe } from "./site/legalPages.he";
import { legalPagesDe } from "./site/legalPages.de";
import { nichePageHe } from "./site/nichePage.he";
import { nichePageDe } from "./site/nichePage.de";
import { publicDemoHe } from "./site/publicDemo.he";
import { publicDemoDe } from "./site/publicDemo.de";
import { publicPricingHe } from "./site/publicPricing.he";
import { publicPricingDe } from "./site/publicPricing.de";
import { roiHe } from "./site/roi.he";
import { roiDe } from "./site/roi.de";

export const siteEn = {
  publicDemo: publicDemoEn,
  roi: roiEn,
  nichePage: nichePageEn,
  legalPages: legalPagesEn,
  publicPricing: publicPricingEn,
} as const;

export const siteRu: Translation<typeof siteEn> = {
  publicDemo: publicDemoRu,
  roi: roiRu,
  nichePage: nichePageRu,
  legalPages: legalPagesRu,
  publicPricing: publicPricingRu,
};

export const siteKa: Translation<typeof siteEn> = {
  publicDemo: publicDemoKa,
  roi: roiKa,
  nichePage: nichePageKa,
  legalPages: legalPagesKa,
  publicPricing: publicPricingKa,
};

export const siteHe: Translation<typeof siteEn> = {
  publicDemo: publicDemoHe,
  roi: roiHe,
  nichePage: nichePageHe,
  legalPages: legalPagesHe,
  publicPricing: publicPricingHe,
};

export const siteDe: Translation<typeof siteEn> = {
  publicDemo: publicDemoDe,
  roi: roiDe,
  nichePage: nichePageDe,
  legalPages: legalPagesDe,
  publicPricing: publicPricingDe,
};
