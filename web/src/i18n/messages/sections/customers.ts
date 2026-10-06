/**
 * Texts of the Customers section and the command palette: the customer
 * list and one customer's page, saved segments, the standing line over a
 * conversation, and the palette (Cmd/Ctrl+K) that finds pages, customers,
 * conversations and bookings.
 *
 * Top-level keys are namespaces. They are spread into the dictionaries of
 * every locale, so they must not clash with the namespaces of the other
 * dictionaries. The other languages are type-checked against `en`.
 *
 * Each namespace lives in its own file per language under `./customers/`;
 * this file composes them.
 */

import type { Translation } from "../../translate";
import { customersEn } from "./customers/customers.en";
import { customersKa } from "./customers/customers.ka";
import { customersRu } from "./customers/customers.ru";
import { paletteEn } from "./customers/palette.en";
import { paletteKa } from "./customers/palette.ka";
import { paletteRu } from "./customers/palette.ru";
import { segmentsEn } from "./customers/segments.en";
import { segmentsKa } from "./customers/segments.ka";
import { segmentsRu } from "./customers/segments.ru";
import { customersHe } from "./customers/customers.he";
import { customersDe } from "./customers/customers.de";
import { paletteHe } from "./customers/palette.he";
import { paletteDe } from "./customers/palette.de";
import { segmentsHe } from "./customers/segments.he";
import { segmentsDe } from "./customers/segments.de";

export const customersSectionEn = {
  customers: customersEn,
  segments: segmentsEn,
  palette: paletteEn,
} as const;

export const customersSectionRu: Translation<typeof customersSectionEn> = {
  customers: customersRu,
  segments: segmentsRu,
  palette: paletteRu,
};

export const customersSectionKa: Translation<typeof customersSectionEn> = {
  customers: customersKa,
  segments: segmentsKa,
  palette: paletteKa,
};

export const customersSectionHe: Translation<typeof customersSectionEn> = {
  customers: customersHe,
  segments: segmentsHe,
  palette: paletteHe,
};

export const customersSectionDe: Translation<typeof customersSectionEn> = {
  customers: customersDe,
  segments: segmentsDe,
  palette: paletteDe,
};
