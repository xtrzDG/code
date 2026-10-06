/**
 * Texts of the cabinet sections: Dashboard and its setup guide, value and reports, the inbox and its conversations, bookings, leads and handoffs.
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
import { conversationMediaEn } from "./insights/conversationMedia.en";
import { conversationMediaKa } from "./insights/conversationMedia.ka";
import { conversationMediaRu } from "./insights/conversationMedia.ru";
import { conversationsEn } from "./insights/conversations.en";
import { conversationsKa } from "./insights/conversations.ka";
import { conversationsRu } from "./insights/conversations.ru";
import { digestChannelsEn } from "./insights/digestChannels.en";
import { digestChannelsKa } from "./insights/digestChannels.ka";
import { digestChannelsRu } from "./insights/digestChannels.ru";
import { dashboardEn } from "./insights/dashboard.en";
import { dashboardKa } from "./insights/dashboard.ka";
import { dashboardRu } from "./insights/dashboard.ru";
import { handoffsEn } from "./insights/handoffs.en";
import { handoffsKa } from "./insights/handoffs.ka";
import { handoffsRu } from "./insights/handoffs.ru";
import { inboxEn } from "./insights/inbox.en";
import { inboxKa } from "./insights/inbox.ka";
import { inboxRu } from "./insights/inbox.ru";
import { inboxCardEn } from "./insights/inboxCard.en";
import { inboxCardKa } from "./insights/inboxCard.ka";
import { inboxCardRu } from "./insights/inboxCard.ru";
import { inboxTriageEn } from "./insights/inboxTriage.en";
import { inboxTriageKa } from "./insights/inboxTriage.ka";
import { inboxTriageRu } from "./insights/inboxTriage.ru";
import { leadsEn } from "./insights/leads.en";
import { leadsKa } from "./insights/leads.ka";
import { leadsRu } from "./insights/leads.ru";
import { messageDeliveryEn } from "./insights/messageDelivery.en";
import { messageDeliveryKa } from "./insights/messageDelivery.ka";
import { messageDeliveryRu } from "./insights/messageDelivery.ru";
import { reportsEn } from "./insights/reports.en";
import { reportsKa } from "./insights/reports.ka";
import { reportsRu } from "./insights/reports.ru";
import { setupGuideEn } from "./insights/setupGuide.en";
import { setupGuideKa } from "./insights/setupGuide.ka";
import { setupGuideRu } from "./insights/setupGuide.ru";
import { sourcesEn } from "./insights/sources.en";
import { sourcesKa } from "./insights/sources.ka";
import { sourcesRu } from "./insights/sources.ru";
import { topicsEn } from "./insights/topics.en";
import { topicsKa } from "./insights/topics.ka";
import { topicsRu } from "./insights/topics.ru";
import { valueEn } from "./insights/value.en";
import { valueKa } from "./insights/value.ka";
import { valueRu } from "./insights/value.ru";

export const insightsEn = {
  insights: insightsCommonEn,
  dashboard: dashboardEn,
  conversations: conversationsEn,
  conversationMedia: conversationMediaEn,
  messageDelivery: messageDeliveryEn,
  bookings: bookingsEn,
  leads: leadsEn,
  handoffs: handoffsEn,
  value: valueEn,
  reports: reportsEn,
  inbox: inboxEn,
  inboxCard: inboxCardEn,
  inboxTriage: inboxTriageEn,
  setupGuide: setupGuideEn,
  sources: sourcesEn,
  topics: topicsEn,
  digestChannels: digestChannelsEn,
} as const;

export const insightsRu: Translation<typeof insightsEn> = {
  insights: insightsCommonRu,
  dashboard: dashboardRu,
  conversations: conversationsRu,
  conversationMedia: conversationMediaRu,
  messageDelivery: messageDeliveryRu,
  bookings: bookingsRu,
  leads: leadsRu,
  handoffs: handoffsRu,
  value: valueRu,
  reports: reportsRu,
  inbox: inboxRu,
  inboxCard: inboxCardRu,
  inboxTriage: inboxTriageRu,
  setupGuide: setupGuideRu,
  sources: sourcesRu,
  topics: topicsRu,
  digestChannels: digestChannelsRu,
};

export const insightsKa: Translation<typeof insightsEn> = {
  insights: insightsCommonKa,
  dashboard: dashboardKa,
  conversations: conversationsKa,
  conversationMedia: conversationMediaKa,
  messageDelivery: messageDeliveryKa,
  bookings: bookingsKa,
  leads: leadsKa,
  handoffs: handoffsKa,
  value: valueKa,
  reports: reportsKa,
  inbox: inboxKa,
  inboxCard: inboxCardKa,
  inboxTriage: inboxTriageKa,
  setupGuide: setupGuideKa,
  sources: sourcesKa,
  topics: topicsKa,
  digestChannels: digestChannelsKa,
};
