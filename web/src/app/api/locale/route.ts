/**
 * POST /api/locale {"locale": "en" | "it"} — change the interface
 * language: stored in a cookie and, for a signed-in user, in the account
 * (PATCH /v1/me) so it follows them to other devices. Answers 204; a body
 * over 1 KB is refused with 413, a request from another site with 403.
 */

import { NextResponse, type NextRequest } from "next/server";
import { z } from "@/lib/zod";

import { LOCALE_COOKIE, isCabinetLanguage } from "@/i18n/config";
import { callBackend, jsonError } from "@/server/backend";
import { BodyTooLargeError, readLimitedText } from "@/server/bodyLimits";
import { localeCookieOptions } from "@/server/cookieSecurity";
import { prepareBackendCall } from "@/server/relay";

export const dynamic = "force-dynamic";

/** {"locale": "it"} needs a few bytes; anything bigger is not a language change. */
const LOCALE_BODY_LIMIT_BYTES = 1024;

const LocaleChange = z.object({ locale: z.string() });

function parseJson(text: string): unknown {
  try {
    return JSON.parse(text);
  } catch {
    return null;
  }
}

export async function POST(request: NextRequest): Promise<Response> {
  const prepared = prepareBackendCall(request, { useSession: true });
  if ("refusal" in prepared) {
    return prepared.refusal;
  }

  let body: string;
  try {
    body = await readLimitedText(request, LOCALE_BODY_LIMIT_BYTES);
  } catch (error) {
    if (error instanceof BodyTooLargeError) {
      return jsonError(413, "payload_too_large", error.message, prepared.requestId);
    }
    throw error;
  }
  const parsed = LocaleChange.safeParse(parseJson(body));
  if (!parsed.success) {
    return jsonError(422, "validation_failed", "Unsupported interface language.", prepared.requestId);
  }
  const locale = parsed.data.locale;
  // Only a language owners can choose (CABINET_LANGUAGES): a draft still being translated is refused.
  if (!isCabinetLanguage(locale)) {
    return jsonError(422, "validation_failed", "Unsupported interface language.", prepared.requestId);
  }

  if (prepared.token) {
    prepared.headers.set("content-type", "application/json");
    prepared.headers.set("accept-language", locale);
    try {
      await callBackend("/v1/me", {
        method: "PATCH",
        headers: prepared.headers,
        body: JSON.stringify({ locale }),
        timeoutMs: 10_000,
      });
    } catch {
      // The cookie still switches the interface; the account keeps its language.
    }
  }

  const response = new NextResponse(null, { status: 204 });
  response.cookies.set(LOCALE_COOKIE, locale, localeCookieOptions(request.headers));
  return response;
}
