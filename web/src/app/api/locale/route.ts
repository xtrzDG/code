/**
 * POST /api/locale {"locale": "ka" | "ru" | "en" | "he" | "de"} — change the interface
 * language: stored in a cookie and, for a signed-in user, in the account
 * (PATCH /v1/me) so it follows them to other devices. Answers 204.
 */

import { NextResponse, type NextRequest } from "next/server";
import { z } from "@/lib/zod";

import { LOCALE_COOKIE, isCabinetLanguage } from "@/i18n/config";
import { callBackend, jsonError, localeCookieOptions } from "@/server/backend";
import { prepareBackendCall } from "@/server/relay";

export const dynamic = "force-dynamic";

const LocaleChange = z.object({ locale: z.string() });

export async function POST(request: NextRequest): Promise<Response> {
  const prepared = prepareBackendCall(request, { useSession: true });
  if ("refusal" in prepared) {
    return prepared.refusal;
  }

  const parsed = LocaleChange.safeParse(await request.json().catch(() => null));
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
  response.cookies.set(LOCALE_COOKIE, locale, localeCookieOptions());
  return response;
}
