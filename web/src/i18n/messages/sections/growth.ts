/**
 * Texts of the waitlist and the return visits: Bookings → Waitlist (who
 * waits for a full day, the place held for one of them, the owner's
 * choices), Bookings → Return visits (the opt-in message that brings
 * customers back) and their bookings as lines of the value hero and the
 * reports.
 *
 * Top-level keys are namespaces. They are spread into en.ts, ru.ts and
 * ka.ts, so they must not clash with the namespaces of the other
 * dictionaries. `ru` and `ka` are type-checked against `en`.
 *
 * Each namespace lives in its own file per language under `./growth/`;
 * this file composes them.
 */

import type { Translation } from "../../translate";
import { growthValueEn } from "./growth/growthValue.en";
import { growthValueKa } from "./growth/growthValue.ka";
import { growthValueRu } from "./growth/growthValue.ru";
import { returnVisitsEn } from "./growth/returnVisits.en";
import { returnVisitsKa } from "./growth/returnVisits.ka";
import { returnVisitsRu } from "./growth/returnVisits.ru";
import { waitlistEn } from "./growth/waitlist.en";
import { waitlistKa } from "./growth/waitlist.ka";
import { waitlistRu } from "./growth/waitlist.ru";
import { growthValueHe } from "./growth/growthValue.he";
import { growthValueDe } from "./growth/growthValue.de";
import { returnVisitsHe } from "./growth/returnVisits.he";
import { returnVisitsDe } from "./growth/returnVisits.de";
import { waitlistHe } from "./growth/waitlist.he";
import { waitlistDe } from "./growth/waitlist.de";

export const growthSectionEn = {
  waitlist: waitlistEn,
  returnVisits: returnVisitsEn,
  growthValue: growthValueEn,
} as const;

export const growthSectionRu: Translation<typeof growthSectionEn> = {
  waitlist: waitlistRu,
  returnVisits: returnVisitsRu,
  growthValue: growthValueRu,
};

export const growthSectionKa: Translation<typeof growthSectionEn> = {
  waitlist: waitlistKa,
  returnVisits: returnVisitsKa,
  growthValue: growthValueKa,
};

export const growthSectionHe: Translation<typeof growthSectionEn> = {
  waitlist: waitlistHe,
  returnVisits: returnVisitsHe,
  growthValue: growthValueHe,
};

export const growthSectionDe: Translation<typeof growthSectionEn> = {
  waitlist: waitlistDe,
  returnVisits: returnVisitsDe,
  growthValue: growthValueDe,
};
