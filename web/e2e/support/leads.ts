/**
 * A leads list served by the test itself: leads come from the assistant's
 * conversations, which an empty test API has none of, so the page's own
 * list call (the BFF path the browser uses) is answered with a page shaped
 * like the API's. Status changes are answered by each test.
 */

import type { Page, Route } from "@playwright/test";

import type { Schema } from "../../src/api/types";

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

/** The status counts of a page that holds just this lead. */
function countsFor(status: LeadStatus): Schema<"LeadStatusCount">[] {
  return (["new", "in_progress", "won", "lost"] as const).map((each) => ({ status: each, count: each === status ? 1 : 0 }));
}

/** Answers GET …/leads with one lead (whatever the tab asks for, the counts stay true). */
export async function serveLeads(page: Page, businessId: string, lead: () => LeadListItem): Promise<void> {
  const path = `/api/backend/v1/businesses/${businessId}/leads`;
  await page.route(
    (url) => url.pathname === path,
    (route) => {
      const current = lead();
      const tab = new URL(route.request().url()).searchParams.get("status");
      const items = tab === null || tab === current.status ? [current] : [];
      return route.fulfill({ json: { items, next_cursor: null, status_counts: countsFor(current.status) } });
    },
  );
}

/** Calls `answer` for every PATCH of the lead; other methods go on. */
export async function onLeadPatch(page: Page, businessId: string, answer: (route: Route) => Promise<void>): Promise<void> {
  await page.route(`**/api/backend/v1/businesses/${businessId}/leads/${LEAD_ID}`, (route) =>
    route.request().method() === "PATCH" ? answer(route) : route.fallback(),
  );
}
