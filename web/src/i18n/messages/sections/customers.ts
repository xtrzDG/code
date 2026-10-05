/**
 * Texts of the Customers section and the command palette: the customer
 * list and one customer's page, saved segments, the standing line over a
 * conversation, and the palette (Cmd/Ctrl+K) that finds pages, customers,
 * conversations and bookings.
 *
 * Top-level keys are namespaces. They are spread into en.ts, ru.ts and
 * ka.ts, so they must not clash with the namespaces of the other
 * dictionaries. `ru` and `ka` are type-checked against `en`.
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
