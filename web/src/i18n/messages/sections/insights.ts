/**
 * Texts of the cabinet sections: Dashboard, conversations, bookings, leads and handoffs.
 *
 * Top-level keys are namespaces (one per section, e.g. `bookings`). They are
 * spread into en.ts, ru.ts and ka.ts, so they must not clash with the
 * namespaces of the other dictionaries. `ru` and `ka` are type-checked
 * against `en`.
 *
 * Each namespace (a large one in a few parts) lives in its own file per
 * language under `./insights/`; this file composes them.
 */

import type { Translation } from "../../translate";
import { bookingsEn } from "./insights/bookings.en";
import { bookingsKa } from "./insights/bookings.ka";
import { bookingsRu } from "./insights/bookings.ru";
import { insightsCommonEn } from "./insights/common.en";
import { insightsCommonKa } from "./insights/common.ka";
import { insightsCommonRu } from "./insights/common.ru";
import { conversationsEn } from "./insights/conversations.en";
import { conversationsKa } from "./insights/conversations.ka";
import { conversationsRu } from "./insights/conversations.ru";
import { dashboardEn } from "./insights/dashboard.en";
import { dashboardKa } from "./insights/dashboard.ka";
import { dashboardRu } from "./insights/dashboard.ru";
import { handoffsEn } from "./insights/handoffs.en";
import { handoffsKa } from "./insights/handoffs.ka";
import { handoffsRu } from "./insights/handoffs.ru";
import { leadsEn } from "./insights/leads.en";
import { leadsKa } from "./insights/leads.ka";
import { leadsRu } from "./insights/leads.ru";

export const insightsEn = {
  insights: insightsCommonEn,
  dashboard: dashboardEn,
  conversations: conversationsEn,
  bookings: bookingsEn,
  leads: leadsEn,
  handoffs: handoffsEn,
} as const;

export const insightsRu: Translation<typeof insightsEn> = {
  insights: insightsCommonRu,
  dashboard: dashboardRu,
  conversations: conversationsRu,
  bookings: bookingsRu,
  leads: leadsRu,
  handoffs: handoffsRu,
};

export const insightsKa: Translation<typeof insightsEn> = {
  insights: insightsCommonKa,
  dashboard: dashboardKa,
  conversations: conversationsKa,
  bookings: bookingsKa,
  leads: leadsKa,
  handoffs: handoffsKa,
};
