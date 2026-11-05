import "server-only";

import { unwrap, type ApiResult } from "@/api/result";

/**
 * The data of a public API call made while rendering a public page (the
 * help center, the status page), or null: the page renders without it and
 * the browser loads it again.
 */
export async function settlePublic<T>(request: Promise<ApiResult<T>>): Promise<T | null> {
  try {
    return await unwrap(request);
  } catch {
    return null;
  }
}
