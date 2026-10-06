/**
 * Typed API client for Client Components.
 *
 * Requests go to the cabinet's own proxy (/api/backend/*), which adds the
 * session's bearer token from an httpOnly cookie: browser code never sees it.
 *
 *     const { data, error } = await api.GET("/v1/businesses/{business_id}", {
 *       params: { path: { business_id: businessId } },
 *     });
 *     // or, throwing ApiError:
 *     const business = await unwrap(api.GET(...));
 */

import createClient, { type Middleware } from "openapi-fetch";

import { loginPath } from "@/lib/navigation";
import { isStepUpChallenge } from "@/lib/stepUpChallenge";

import { idempotencyKeys } from "./idempotencyKey";
import type { paths } from "./schema";
import { stepUpRetry } from "./stepUp";

export const BFF_BASE_PATH = "/api/backend";

/**
 * A 401 from the API means the session is gone: go to the sign-in page.
 * Not a step-up challenge (the session is fine; see stepUp.ts).
 */
const redirectOnSessionExpiry: Middleware = {
  onResponse({ response }) {
    if (response.status === 401 && typeof window !== "undefined" && !isStepUpChallenge(response.status, response.headers)) {
      const next = `${window.location.pathname}${window.location.search}`;
      window.location.assign(loginPath({ next, reason: "expired" }));
    }
    return undefined;
  },
};

export const api = createClient<paths>({
  baseUrl: BFF_BASE_PATH,
  credentials: "same-origin",
  headers: { Accept: "application/json" },
});

api.use(redirectOnSessionExpiry);
api.use(idempotencyKeys);
api.use(stepUpRetry);
