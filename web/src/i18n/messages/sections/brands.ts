/**
 * Texts of brands (/brands): a chain's locations under one brand, its
 * combined overview, its team and the answers its locations share.
 *
 * Top-level keys are namespaces. They are spread into the dictionaries of
 * every locale, so they must not clash with the namespaces of the other
 * dictionaries. The other languages are type-checked against `en`.
 */

import type { Translation } from "../../translate";
import { brandsDe } from "./brands/brands.de";
import { brandsEn } from "./brands/brands.en";
import { brandsHe } from "./brands/brands.he";
import { brandsKa } from "./brands/brands.ka";
import { brandsRu } from "./brands/brands.ru";

export const brandsSectionEn = { brands: brandsEn } as const;

export const brandsSectionRu: Translation<typeof brandsSectionEn> = { brands: brandsRu };

export const brandsSectionKa: Translation<typeof brandsSectionEn> = { brands: brandsKa };

export const brandsSectionHe: Translation<typeof brandsSectionEn> = { brands: brandsHe };

export const brandsSectionDe: Translation<typeof brandsSectionEn> = { brands: brandsDe };
