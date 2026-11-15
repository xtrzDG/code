import "server-only";

import type { LoginMethod } from "@/lib/countries";
import { getServerApi } from "@/server/api";
import { settlePublic } from "@/server/publicData";

import { openingLoginMethod } from "./loginOptions";

/** The page's first HTML waits this long for the options, then opens on phone. */
const OPTIONS_TIMEOUT_MS = 2_000;

/**
 * The form in the sign-in page's first HTML, read from the API while the
 * page renders. Choosing it in the browser instead, once its own check of
 * the options has answered, replaced the phone form under a visitor who
 * was already typing: the field, its focus and its error went away. An
 * API that does not answer in time, or at all, opens the page on phone,
 * where the browser's check explains what works.
 */
export async function loadOpeningLoginMethod(): Promise<LoginMethod> {
  try {
    const api = await getServerApi();
    const options = await settlePublic(
      api.GET("/v1/auth/login-options", { params: { query: {} }, signal: AbortSignal.timeout(OPTIONS_TIMEOUT_MS) }),
    );
    return options ? openingLoginMethod(options) : "phone";
  } catch {
    // No API address (BACKEND_URL): the page still renders, and its own calls say what is wrong.
    return "phone";
  }
}
