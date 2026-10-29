/**
 * Texts of brands (/brands): a chain's locations under one brand, its
 * combined overview, its team and the answers its locations share.
 *
 * Top-level keys are namespaces. They are spread into the dictionaries of
 * every locale, so they must not clash with the namespaces of the other
 * dictionaries. The other languages are type-checked against `en`.
 */

import type { Translation } from "../../translate";
import { brandsIt } from "./brands/brands.it";
import { brandsEn } from "./brands/brands.en";

export const brandsSectionEn = { brands: brandsEn } as const;

export const brandsSectionIt: Translation<typeof brandsSectionEn> = { brands: brandsIt };
