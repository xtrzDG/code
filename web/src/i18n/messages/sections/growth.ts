/**
 * Texts of the waitlist, the return visits and the deposits: Bookings →
 * Waitlist (who waits for a full day, the place held for one of them, the
 * owner's choices), Bookings → Return visits (the opt-in message that
 * brings customers back), their bookings as lines of the value hero and
 * the reports, and the deposits that hold a booking until it is paid.
 *
 * Top-level keys are namespaces. They are spread into the dictionaries of
 * every locale, so they must not clash with the namespaces of the other
 * dictionaries. The other languages are type-checked against `en`.
 *
 * Each namespace lives in its own file per language under `./growth/`;
 * this file composes them.
 */

import type { Translation } from "../../translate";
import { depositsIt } from "./growth/deposits.it";
import { depositsEn } from "./growth/deposits.en";
import { growthValueEn } from "./growth/growthValue.en";
import { returnVisitsEn } from "./growth/returnVisits.en";
import { waitlistEn } from "./growth/waitlist.en";
import { growthValueIt } from "./growth/growthValue.it";
import { returnVisitsIt } from "./growth/returnVisits.it";
import { waitlistIt } from "./growth/waitlist.it";

export const growthSectionEn = {
  waitlist: waitlistEn,
  returnVisits: returnVisitsEn,
  growthValue: growthValueEn,
  deposits: depositsEn,
} as const;

export const growthSectionIt: Translation<typeof growthSectionEn> = {
  waitlist: waitlistIt,
  returnVisits: returnVisitsIt,
  growthValue: growthValueIt,
  deposits: depositsIt,
};
