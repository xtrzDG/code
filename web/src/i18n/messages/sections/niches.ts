/**
 * Texts of the platform admin's niche template editor (/admin/niches): the
 * words new owners read in the tunnel and the profile wizard.
 *
 * Top-level keys are namespaces. They are spread into the dictionaries of
 * every locale, so they must not clash with the namespaces of the other
 * dictionaries. The other languages are type-checked against `en`.
 *
 * Each namespace lives in its own file per language under `./niches/`;
 * this file composes them.
 */

import type { Translation } from "../../translate";
import { adminNichesDe } from "./niches/adminNiches.de";
import { adminNichesEn } from "./niches/adminNiches.en";
import { adminNichesHe } from "./niches/adminNiches.he";
import { adminNichesKa } from "./niches/adminNiches.ka";
import { adminNichesRu } from "./niches/adminNiches.ru";

export const nichesSectionEn = {
  adminNiches: adminNichesEn,
} as const;

export const nichesSectionRu: Translation<typeof nichesSectionEn> = {
  adminNiches: adminNichesRu,
};

export const nichesSectionKa: Translation<typeof nichesSectionEn> = {
  adminNiches: adminNichesKa,
};

export const nichesSectionHe: Translation<typeof nichesSectionEn> = {
  adminNiches: adminNichesHe,
};

export const nichesSectionDe: Translation<typeof nichesSectionEn> = {
  adminNiches: adminNichesDe,
};
