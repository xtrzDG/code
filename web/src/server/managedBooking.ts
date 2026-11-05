import "server-only";

import { headers } from "next/headers";
import { cache } from "react";

import { unwrap } from "@/api/result";
import type { Schema } from "@/api/types";
import { primaryLanguage } from "@/lib/hostedChat/language";
import { chooseLanguage } from "@/lib/hostedChat/negotiate";
import { bookingProblem, type BookingProblem } from "@/lib/bookingPage/refusals";
import { BOOKING_PAGE_LANGUAGES, hasBookingPageTexts } from "@/lib/bookingPage/texts";

import { getServerApi } from "./api";

/**
 * A guest's booking page (/r/{token}) asks the API's public
 * GET /v1/public/bookings/{token} once per view (the metadata and the page
 * share the answer). The token is the key: it is not logged and goes to
 * the API only.
 */

type ManagedBookingView = Schema<"ManagedBookingView">;

export type ManagedBookingLookup =
  | { kind: "found"; view: ManagedBookingView }
  | { kind: "refused"; problem: BookingProblem };

/** The token's alphabet and length (the API's BookingManageToken). */
const TOKEN_PATTERN = /^[A-Za-z0-9_-]{40,120}$/;

function isManageToken(value: string): boolean {
  return TOKEN_PATTERN.test(value);
}

export const loadManagedBooking = cache(async (token: string): Promise<ManagedBookingLookup> => {
  if (!isManageToken(token)) {
    return { kind: "refused", problem: "linkInvalid" };
  }
  try {
    const api = await getServerApi();
    const view = await unwrap(api.GET("/v1/public/bookings/{token}", { params: { path: { token } } }));
    return { kind: "found", view };
  } catch (error) {
    return { kind: "refused", problem: bookingProblem(error) };
  }
});

/**
 * The page's language: the guest's booking language when the page has
 * texts in it; without a booking the browser's languages; else English.
 */
export async function bookingPageLanguage(lookup: ManagedBookingLookup): Promise<string> {
  if (lookup.kind === "found" && hasBookingPageTexts(lookup.view.language)) {
    return primaryLanguage(lookup.view.language);
  }
  const acceptLanguage = (await headers()).get("accept-language");
  return chooseLanguage(acceptLanguage, BOOKING_PAGE_LANGUAGES, "en");
}
