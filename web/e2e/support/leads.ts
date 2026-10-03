/**
 * A request (lead) on a conversation card served by the test itself:
 * requests come from the assistant's conversations, which an empty test
 * API has none of (see support/conversation-card.ts). Status changes are
 * answered by each test.
 */

import type { Page, Route } from "@playwright/test";

import type { Schema } from "../../src/api/types";

import { conversationCard, type ConversationDetail } from "./conversation-card";

export type LeadListItem = Schema<"LeadListItem">;
type LeadStatus = LeadListItem["status"];

export const LEAD_ID = "lead_2c4e6a8b-1d3f-4a5b-9c7d-8e9f0a1b2c3d";
export const LEAD_CUSTOMER = "Nino Beridze";

export function leadOf(businessId: string, status: LeadStatus): LeadListItem {
  return {
    id: LEAD_ID,
    business_id: businessId,
    contact_id: "contact_5b7d9f1a-2c4e-4a6b-8d0f-1a3c5e7a9b2d",
    contact_name: LEAD_CUSTOMER,
    contact_phone_number: "+995555123456",
    lead_type: "banquet",
    details: "Birthday dinner for 40 guests on a Saturday evening",
    source_channel: "whatsapp",
    status,
    party_size: 40,
    is_sandbox: false,
    created_at: (Date.now() - 3_600_000) * 1000,
  };
}

/** The served conversation of the request's customer, with the request on it. */
export function cardWithLead(businessId: string, lead: LeadListItem): ConversationDetail {
  const card = conversationCard(businessId, { leads: [lead] });
  card.conversation.contact_name = LEAD_CUSTOMER;
  return card;
}

/** Calls `answer` for every PATCH of the lead; other methods go on. */
export async function onLeadPatch(page: Page, businessId: string, answer: (route: Route) => Promise<void>): Promise<void> {
  await page.route(`**/api/backend/v1/businesses/${businessId}/leads/${LEAD_ID}`, (route) =>
    route.request().method() === "PATCH" ? answer(route) : route.fallback(),
  );
}
