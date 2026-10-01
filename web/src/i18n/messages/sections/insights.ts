/**
 * Texts of the cabinet sections: Dashboard, conversations, bookings, leads and handoffs.
 *
 * Top-level keys are namespaces (one per section, e.g. `bookings`). They are
 * spread into en.ts, ru.ts and ka.ts, so they must not clash with the
 * namespaces of the other dictionaries. `ru` and `ka` are type-checked
 * against `en`.
 */

import type { Translation } from "../../translate";

export const insightsEn = {} as const;

export const insightsRu: Translation<typeof insightsEn> = {};

export const insightsKa: Translation<typeof insightsEn> = {};
