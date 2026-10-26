/**
 * The demo restaurant "Mtsvane Ezo" (SEED_DEMO_DATA, support/demo.ts), whose
 * conversations, bookings, customers and knowledge fill the pages of the
 * visual tests: signed in as its owner, with the conversations to open.
 *
 * The owner signs in once per run (platform.spec.ts, the project every
 * other visual test waits for): an address gets a login code at most every
 * 30 seconds, and the tests run on several workers. Their one-time tips
 * are put away there too: a phone counts a tip as seen after a moment on
 * screen, so whether the next page still shows it would depend on timing.
 */

import { readFileSync, writeFileSync } from "node:fs";
import path from "node:path";

import type { APIRequestContext, BrowserContext } from "@playwright/test";

import { signInAsDemoOwner } from "../support/demo";
import { API_URL, ARTIFACTS_DIRECTORY } from "../support/env";
import { expect, signInContext } from "../support/fixtures";

const OWNER_PATH = path.join(ARTIFACTS_DIRECTORY, "visual-demo-owner.json");
/** The one-time tips (src/lib/help/helpTopics.ts COACH_MARKS). */
const TIPS = ["inbox", "assistant", "channels"] as const;

export interface Restaurant {
  token: string;
  businessId: string;
  /** Its hosted chat page's address (`/c/{slug}`). */
  slug: string;
}

/** Signs the demo owner in for this run, puts their tips away and keeps the session for the other workers. */
export async function signInRestaurantOwner(request: APIRequestContext): Promise<Restaurant> {
  const owner = await signInAsDemoOwner(request);
  const headers = { authorization: `Bearer ${owner.token}` };
  for (const tip of TIPS) {
    const seen = await request.put(`${API_URL}/v1/me/help/coach-marks/${tip}`, { headers });
    expect(seen.ok(), await seen.text()).toBe(true);
  }
  const links = await request.get(`${API_URL}/v1/businesses/${owner.businessId}/share-links`, { headers });
  expect(links.ok(), await links.text()).toBe(true);
  const restaurant = { ...owner, slug: ((await links.json()) as { slug: string }).slug };
  writeFileSync(OWNER_PATH, JSON.stringify(restaurant));
  return restaurant;
}

/** Signs the context in as the demo owner (signed in by platform.spec.ts). */
export async function openRestaurant(context: BrowserContext): Promise<Restaurant> {
  const restaurant = JSON.parse(readFileSync(OWNER_PATH, "utf8")) as Restaurant;
  await signInContext(context, restaurant.token);
  return restaurant;
}

interface ConversationRow {
  id: string;
  contact_name?: string | null;
}

/** The id of the restaurant's conversation with this guest. */
export async function conversationWith(request: APIRequestContext, restaurant: Restaurant, guest: string): Promise<string> {
  const response = await request.get(`${API_URL}/v1/businesses/${restaurant.businessId}/conversations`, {
    headers: { authorization: `Bearer ${restaurant.token}` },
    params: { limit: 100 },
  });
  expect(response.ok(), await response.text()).toBe(true);
  const found = ((await response.json()) as { items: ConversationRow[] }).items.find((row) => row.contact_name === guest);
  expect(found, `the demo restaurant talks with ${guest}`).toBeDefined();
  return found!.id;
}

/** The id of the restaurant's customer of this name. */
export async function customerNamed(request: APIRequestContext, restaurant: Restaurant, name: string): Promise<string> {
  const response = await request.get(`${API_URL}/v1/businesses/${restaurant.businessId}/contacts`, {
    headers: { authorization: `Bearer ${restaurant.token}` },
    params: { search: name },
  });
  expect(response.ok(), await response.text()).toBe(true);
  const items = ((await response.json()) as { items: { id: string; name?: string | null }[] }).items;
  const found = items.find((item) => item.name === name);
  expect(found, `the demo restaurant knows ${name}`).toBeDefined();
  return found!.id;
}

/** "/b/{id}/assistant/knowledge/import" → "restaurant-assistant-knowledge-import". */
export function screenOf(path: string, businessId: string): string {
  const [page, query] = path.replace(`/b/${businessId}/`, "").replace(/^\//, "").split("?");
  return ["restaurant", ...page!.split("/"), ...(query ? [query.replace(/[=&]/g, "-")] : [])].join("-");
}
