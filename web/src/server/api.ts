import "server-only";

import { cookies, headers } from "next/headers";
import { notFound, redirect } from "next/navigation";
import createClient, { type Client } from "openapi-fetch";
import { cache } from "react";

import { isApiError } from "@/api/errors";
import { unwrap, type ApiResult } from "@/api/result";
import type { paths } from "@/api/schema";
import type { BusinessView, CurrentUserView } from "@/api/types";
import { getLocale } from "@/i18n/server";
import { ADMIN_PATH, adminClientPath, businessLocation, securityPath } from "@/lib/navigation";

import { PATHNAME_HEADER, buildUpstreamHeaders, getBackendUrl, sanitizeRequestId } from "./backend";
import { readSessionToken } from "./sessionCookie";

/**
 * Typed API client for Server Components, authenticated with the session
 * cookie. Prefer `serverFetch(...)` around its calls. The browser's
 * User-Agent and the client address the cabinet's proxies vouch for go
 * along, so the API records the session's device, not the cabinet server.
 */
export async function getServerApi(): Promise<Client<paths>> {
  const [cookieStore, locale, incoming] = await Promise.all([cookies(), getLocale(), headers()]);
  const upstreamHeaders = buildUpstreamHeaders(incoming, {
    token: readSessionToken(cookieStore),
    locale,
    requestId: sanitizeRequestId(null),
  });
  return createClient<paths>({
    baseUrl: getBackendUrl(),
    headers: Object.fromEntries(upstreamHeaders.entries()),
    cache: "no-store",
  });
}

/** True when the request carries a session cookie (it may still be expired). */
export async function hasSession(): Promise<boolean> {
  return readSessionToken(await cookies()) !== undefined;
}

async function expiredSessionUrl(): Promise<string> {
  const pathname = (await headers()).get(PATHNAME_HEADER);
  return pathname ? `/api/auth/expired?next=${encodeURIComponent(pathname)}` : "/api/auth/expired";
}

/**
 * The data of an API call made from a Server Component:
 *  - 401: the session is over -> sign-in page (the cookie is dropped);
 *  - 404 (also another tenant's id) -> the not-found page;
 *  - 403 `mfa_required` (a business that requires two-factor sign-in, the
 *    admin pages) -> Account → Security, then back;
 *  - anything else throws ApiError to the nearest error.tsx.
 *
 *     const api = await getServerApi();
 *     const me = await serverFetch(api.GET("/v1/me"));
 */
export async function serverFetch<T>(request: Promise<ApiResult<T>>): Promise<T> {
  try {
    return await unwrap(request);
  } catch (error) {
    if (isApiError(error) && error.status === 401) {
      redirect(await expiredSessionUrl());
    }
    if (isApiError(error) && error.status === 404) {
      notFound();
    }
    if (isApiError(error) && error.status === 403 && error.reasons.some((reason) => reason.code === "support_access_required")) {
      // A platform admin opens a client's cabinet only with a reason, from the admin pages.
      const businessId = businessLocation((await headers()).get(PATHNAME_HEADER) ?? "")?.businessId;
      if (businessId) {
        redirect(adminClientPath(businessId));
      }
    }
    if (isApiError(error) && error.status === 403 && error.reasons.some((reason) => reason.code === "mfa_required")) {
      const pathname = (await headers()).get(PATHNAME_HEADER);
      redirect(securityPath({ reason: pathname?.startsWith(ADMIN_PATH) ? "admin" : "business", next: pathname }));
    }
    throw error;
  }
}

/** The signed-in user and their memberships (deduplicated per request). */
export const getCurrentUser = cache(async (): Promise<CurrentUserView> => {
  const api = await getServerApi();
  return serverFetch(api.GET("/v1/me"));
});

/** One business the user may open (deduplicated per request). */
export const getBusiness = cache(async (businessId: string): Promise<BusinessView> => {
  const api = await getServerApi();
  return serverFetch(
    api.GET("/v1/businesses/{business_id}", { params: { path: { business_id: businessId } } }),
  );
});
