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
import { adminNichesIt } from "./niches/adminNiches.it";
import { adminNichesEn } from "./niches/adminNiches.en";

export const nichesSectionEn = {
  adminNiches: adminNichesEn,
} as const;

export const nichesSectionIt: Translation<typeof nichesSectionEn> = {
  adminNiches: adminNichesIt,
};
