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

import {
  PATHNAME_HEADER,
  SESSION_COOKIE,
  buildUpstreamHeaders,
  getBackendUrl,
  sanitizeRequestId,
} from "./backend";

/**
 * Typed API client for Server Components, authenticated with the session
 * cookie. Prefer `serverFetch(...)` around its calls.
 */
export async function getServerApi(): Promise<Client<paths>> {
  const [cookieStore, locale] = await Promise.all([cookies(), getLocale()]);
  const upstreamHeaders = buildUpstreamHeaders(null, {
    token: cookieStore.get(SESSION_COOKIE)?.value,
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
  return (await cookies()).has(SESSION_COOKIE);
}

async function expiredSessionUrl(): Promise<string> {
  const pathname = (await headers()).get(PATHNAME_HEADER);
  return pathname ? `/api/auth/expired?next=${encodeURIComponent(pathname)}` : "/api/auth/expired";
}

/**
 * The data of an API call made from a Server Component:
 *  - 401: the session is over -> sign-in page (the cookie is dropped);
 *  - 404 (also another tenant's id) -> the not-found page;
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
