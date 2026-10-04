/**
 * The proxy's part for the hosted chat page (/c/{address}): look the
 * address up, move an older address (or the business id) to the current
 * one, and give the page its strict policy with the API's origin (the
 * cabinet's live preview, ?preview=1, may be framed by the cabinet). Every
 * /c/ page is kept out of search engines (X-Robots-Tag, besides the
 * page's own robots meta tag).
 */

import { NextResponse, type NextRequest } from "next/server";

import { isPreviewRequest } from "@/lib/hostedChat/preview";

import { PATHNAME_HEADER, isCookieSecure } from "./backend";
import { NONCE_HEADER, buildHostedChatPolicy, createNonce } from "./contentSecurityPolicy";
import {
  HOSTED_CHAT_HEADER,
  chatApiBase,
  encodeLookup,
  hostedChatPath,
  lookUpHostedChat,
  originOf,
} from "./hostedChat";

export const CSP_HEADER = "content-security-policy";
export const ROBOTS_HEADER = "x-robots-tag";
export const NOINDEX = "noindex, nofollow";

export async function routeHostedChat(request: NextRequest, address: string): Promise<NextResponse> {
  const { pathname, search } = request.nextUrl;
  const lookup = await lookUpHostedChat(address, request.headers);
  if (lookup.kind === "found" && lookup.view.slug && lookup.view.slug !== address) {
    // Printed QR codes keep the old address: it leads to the current one.
    const response = NextResponse.redirect(new URL(hostedChatPath(lookup.view.slug, search), request.url), 308);
    response.headers.set(ROBOTS_HEADER, NOINDEX);
    return response;
  }

  const nonce = createNonce();
  const policy = buildHostedChatPolicy({
    nonce,
    apiOrigin: lookup.kind === "found" ? originOf(chatApiBase(lookup.view)) : null,
    isDevelopment: process.env.NODE_ENV === "development",
    isHttps: isCookieSecure(),
    isPreview: isPreviewRequest(request.nextUrl.searchParams),
  });
  const requestHeaders = new Headers(request.headers);
  requestHeaders.set(PATHNAME_HEADER, `${pathname}${search}`);
  requestHeaders.set(CSP_HEADER, policy);
  requestHeaders.set(NONCE_HEADER, nonce);
  requestHeaders.set(HOSTED_CHAT_HEADER, encodeLookup(lookup));

  const response = NextResponse.next({ request: { headers: requestHeaders } });
  response.headers.set(CSP_HEADER, policy);
  response.headers.set(ROBOTS_HEADER, NOINDEX);
  return response;
}
