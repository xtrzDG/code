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
import { paletteEn } from "./customers/palette.en";
import { segmentsEn } from "./customers/segments.en";
import { customersIt } from "./customers/customers.it";
import { paletteIt } from "./customers/palette.it";
import { segmentsIt } from "./customers/segments.it";

export const customersSectionEn = {
  customers: customersEn,
  segments: segmentsEn,
  palette: paletteEn,
} as const;

export const customersSectionIt: Translation<typeof customersSectionEn> = {
  customers: customersIt,
  segments: segmentsIt,
  palette: paletteIt,
};
