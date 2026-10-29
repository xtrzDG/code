/**
 * Texts of the cabinet sections: Dashboard and its setup guide, value and reports, the inbox and its conversations, bookings, leads and handoffs.
 *
 * Top-level keys are namespaces (one per section, e.g. `bookings`). They are
 * spread into en.ts and it.ts, so they must not clash
 * with the namespaces of the other dictionaries. The other languages are
 * type-checked against `en`.
 *
 * Each namespace (a large one in a few parts) lives in its own file per
 * language under `./insights/`; this file composes them.
 */

import type { Translation } from "../../translate";
import { bookingCalendarIt } from "./insights/bookingCalendar.it";
import { bookingCalendarEn } from "./insights/bookingCalendar.en";
import { bookingsEn } from "./insights/bookings.en";
import { insightsCommonEn } from "./insights/common.en";
import { conversationMediaEn } from "./insights/conversationMedia.en";
import { conversationsEn } from "./insights/conversations.en";
import { digestChannelsEn } from "./insights/digestChannels.en";
import { dashboardEn } from "./insights/dashboard.en";
import { handoffsEn } from "./insights/handoffs.en";
import { inboxEn } from "./insights/inbox.en";
import { inboxCardEn } from "./insights/inboxCard.en";
import { inboxTriageEn } from "./insights/inboxTriage.en";
import { leadsEn } from "./insights/leads.en";
import { messageDeliveryEn } from "./insights/messageDelivery.en";
import { overviewPhoneEn } from "./insights/overviewPhone.en";
import { reportsEn } from "./insights/reports.en";
import { setupGuideEn } from "./insights/setupGuide.en";
import { sourcesEn } from "./insights/sources.en";
import { topicsEn } from "./insights/topics.en";
import { valueEn } from "./insights/value.en";
import { bookingsIt } from "./insights/bookings.it";
import { insightsCommonIt } from "./insights/common.it";
import { conversationMediaIt } from "./insights/conversationMedia.it";
import { conversationsIt } from "./insights/conversations.it";
import { digestChannelsIt } from "./insights/digestChannels.it";
import { dashboardIt } from "./insights/dashboard.it";
import { handoffsIt } from "./insights/handoffs.it";
import { inboxIt } from "./insights/inbox.it";
import { inboxCardIt } from "./insights/inboxCard.it";
import { inboxTriageIt } from "./insights/inboxTriage.it";
import { leadsIt } from "./insights/leads.it";
import { messageDeliveryIt } from "./insights/messageDelivery.it";
import { overviewPhoneIt } from "./insights/overviewPhone.it";
import { reportsIt } from "./insights/reports.it";
import { setupGuideIt } from "./insights/setupGuide.it";
import { sourcesIt } from "./insights/sources.it";
import { topicsIt } from "./insights/topics.it";
import { valueIt } from "./insights/value.it";

export const insightsEn = {
  insights: insightsCommonEn,
  dashboard: dashboardEn,
  conversations: conversationsEn,
  conversationMedia: conversationMediaEn,
  messageDelivery: messageDeliveryEn,
  bookings: bookingsEn,
  bookingCalendar: bookingCalendarEn,
  leads: leadsEn,
  handoffs: handoffsEn,
  value: valueEn,
  reports: reportsEn,
  inbox: inboxEn,
  inboxCard: inboxCardEn,
  inboxTriage: inboxTriageEn,
  overviewPhone: overviewPhoneEn,
  setupGuide: setupGuideEn,
  sources: sourcesEn,
  topics: topicsEn,
  digestChannels: digestChannelsEn,
} as const;

export const insightsIt: Translation<typeof insightsEn> = {
  insights: insightsCommonIt,
  dashboard: dashboardIt,
  conversations: conversationsIt,
  conversationMedia: conversationMediaIt,
  messageDelivery: messageDeliveryIt,
  bookings: bookingsIt,
  bookingCalendar: bookingCalendarIt,
  leads: leadsIt,
  handoffs: handoffsIt,
  value: valueIt,
  reports: reportsIt,
  inbox: inboxIt,
  inboxCard: inboxCardIt,
  inboxTriage: inboxTriageIt,
  overviewPhone: overviewPhoneIt,
  setupGuide: setupGuideIt,
  sources: sourcesIt,
  topics: topicsIt,
  digestChannels: digestChannelsIt,
};
