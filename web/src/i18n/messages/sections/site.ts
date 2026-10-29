/**
 * Texts of the public site around the cabinet: the landing page's live
 * demo and value calculator, the pages of each kind of business, the
 * legal and contact pages and the honest price notes.
 *
 * Top-level keys are namespaces; they are spread into the dictionaries
 * of every locale. The other languages are type-checked against `en`.
 */

import type { Translation } from "../../translate";
import { legalPagesEn } from "./site/legalPages.en";
import { nichePageEn } from "./site/nichePage.en";
import { publicDemoEn } from "./site/publicDemo.en";
import { publicPricingEn } from "./site/publicPricing.en";
import { roiEn } from "./site/roi.en";
import { legalPagesIt } from "./site/legalPages.it";
import { nichePageIt } from "./site/nichePage.it";
import { publicDemoIt } from "./site/publicDemo.it";
import { publicPricingIt } from "./site/publicPricing.it";
import { roiIt } from "./site/roi.it";

export const siteEn = {
  publicDemo: publicDemoEn,
  roi: roiEn,
  nichePage: nichePageEn,
  legalPages: legalPagesEn,
  publicPricing: publicPricingEn,
} as const;

export const siteIt: Translation<typeof siteEn> = {
  publicDemo: publicDemoIt,
  roi: roiIt,
  nichePage: nichePageIt,
  legalPages: legalPagesIt,
  publicPricing: publicPricingIt,
};
