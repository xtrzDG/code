/** A business whose hosted chat page works, for the hosted chat and Share tests. */

import { expect, type APIRequestContext } from "@playwright/test";

import { createAssistant, createBusiness, uniqueSuffix } from "./api";
import { API_URL } from "./env";

export interface ChatBusiness {
  id: string;
  name: string;
  slug: string;
}

/** A business with English, Georgian and Hebrew customers and its website chat on. */
export async function openChatBusiness(request: APIRequestContext, token: string): Promise<ChatBusiness> {
  const name = `Café Shalom ${uniqueSuffix()}`;
  const headers = { authorization: `Bearer ${token}` };
  const id = await createBusiness(request, token, {
    name,
    niche_key: "restaurant",
    country_code: "GE",
    city: "Tbilisi",
    languages: ["en", "ka", "he"],
    default_language: "en",
  });
  await createAssistant(request, token, id);
  const connected = await request.put(`${API_URL}/v1/businesses/${id}/channels/web`, { data: {}, headers });
  expect(connected.ok(), await connected.text()).toBe(true);
  // The first look at the share links gives the business its address.
  const links = await request.get(`${API_URL}/v1/businesses/${id}/share-links`, { headers });
  expect(links.ok(), await links.text()).toBe(true);
  return { id, name, slug: ((await links.json()) as { slug: string }).slug };
}
