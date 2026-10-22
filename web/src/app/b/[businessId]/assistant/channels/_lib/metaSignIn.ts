/**
 * "Continue with Facebook" on Meta's channels, as pure helpers: which
 * sign-in a channel uses, what Facebook's window opens with, the messages
 * of WhatsApp's signup window (read only from Facebook's own origins), and
 * the address that reopens the dialog in a document allowed to open
 * Facebook (lib/metaSignInPages.ts).
 */

import type { RequestBody, Schema } from "@/api/types";
import { isMetaSignInPage } from "@/lib/metaSignInPages";

import type { ConnectableChannel } from "./channels";

export type MetaSignInOptions = Schema<"MetaSignInOptionsView">;
export type MetaSignInStart = Schema<"MetaConnectionStartView">;
export type MetaPage = Schema<"MetaPageView">;
type MetaPurpose = Schema<"MetaConnectionPurpose">;
export type CompleteSignupBody = RequestBody<"/v1/businesses/{business_id}/channels/whatsapp/embedded-signup", "post">;

/** The channels that connect through a Facebook sign-in. */
export type MetaChannel = "whatsapp" | "instagram" | "messenger";

export function isMetaChannel(kind: ConnectableChannel | null): kind is MetaChannel {
  return kind === "whatsapp" || kind === "instagram" || kind === "messenger";
}

/** WhatsApp has Embedded Signup; Instagram and Messenger pick a Facebook page. */
export function purposeOf(kind: MetaChannel): MetaPurpose {
  return kind === "whatsapp" ? "whatsapp" : "pages";
}

/** Whether this server offers "Continue with Facebook" for the channel. */
export function offersFacebook(options: MetaSignInOptions | undefined, kind: MetaChannel): boolean {
  if (!options?.app_id || !options.graph_api_version) {
    return false;
  }
  return kind === "whatsapp" ? options.whatsapp : options.pages;
}

/**
 * What FB.login opens with: Embedded Signup's configuration (it asks for the
 * WhatsApp permissions itself) or the page picker's permissions. Either way
 * Facebook answers with a short-lived code that only the server exchanges.
 */
export function facebookLoginOptions(start: MetaSignInStart): Record<string, unknown> {
  if (start.purpose === "whatsapp") {
    return {
      config_id: start.configuration_id,
      response_type: "code",
      override_default_response_type: true,
      extras: { setup: {}, featureType: "", sessionInfoVersion: "3" },
    };
  }
  return {
    scope: (start.permissions ?? []).join(","),
    response_type: "code",
    override_default_response_type: true,
    return_scopes: true,
    auth_type: "rerequest",
  };
}

/** The origins Facebook's sign-in windows post their messages from (exactly these). */
const FACEBOOK_ORIGINS: ReadonlySet<string> = new Set(["https://www.facebook.com", "https://web.facebook.com"]);
const MAX_MESSAGE_LENGTH = 10_000;
const META_ID = /^[0-9]{1,32}$/;

/** What WhatsApp's signup window reported: the chosen account and number, or where the owner stopped. */
export type SignupSession =
  | { event: "finish"; businessAccountId: string | null; phoneNumberId: string | null }
  | { event: "cancel" }
  | { event: "error" };

function isRecord(value: unknown): value is Record<string, unknown> {
  return typeof value === "object" && value !== null && !Array.isArray(value);
}

function metaId(value: unknown): string | null {
  return typeof value === "string" && META_ID.test(value) ? value : null;
}

/**
 * A `message` event of WhatsApp's signup window, or null for anything else:
 * a message from any other origin is never read, and only the session's
 * event and numeric ids are taken from it.
 */
export function readSignupMessage(origin: string, data: unknown): SignupSession | null {
  if (!FACEBOOK_ORIGINS.has(origin)) {
    return null;
  }
  let message: unknown = data;
  if (typeof data === "string") {
    if (data.length > MAX_MESSAGE_LENGTH) {
      return null;
    }
    try {
      message = JSON.parse(data);
    } catch {
      return null;
    }
  }
  if (!isRecord(message) || message.type !== "WA_EMBEDDED_SIGNUP") {
    return null;
  }
  const details = isRecord(message.data) ? message.data : {};
  switch (message.event) {
    case "FINISH":
    case "FINISH_ONLY_WABA":
      return { event: "finish", businessAccountId: metaId(details.waba_id), phoneNumberId: metaId(details.phone_number_id) };
    case "CANCEL":
      return { event: "cancel" };
    case "ERROR":
      return { event: "error" };
    default:
      return null;
  }
}

/** The body that finishes Embedded Signup: the code, and the ids the window reported. */
export function completeSignupBody(state: string, code: string, session: SignupSession | null): CompleteSignupBody {
  const finished = session?.event === "finish" ? session : null;
  return {
    state,
    code,
    ...(finished?.businessAccountId ? { whatsapp_business_account_id: finished.businessAccountId } : {}),
    ...(finished?.phoneNumberId ? { phone_number_id: finished.phoneNumberId } : {}),
  };
}

/** The page's name as the picker shows it (its username, or its id, when it has none). */
export function pageTitle(page: MetaPage): string {
  return page.name?.trim() || page.username || page.page_id;
}

/**
 * Whether the document this page runs in was loaded as a page allowed to
 * open Facebook. A page reached by in-app navigation keeps the headers of
 * the document it started in. Without the navigation entry (very old
 * browsers) it is taken as allowed rather than looping.
 */
export function documentAllowsFacebook(documentUrl: string | null): boolean {
  if (documentUrl === null) {
    return true;
  }
  try {
    return isMetaSignInPage(new URL(documentUrl).pathname);
  } catch {
    return false;
  }
}

/** The address this document was loaded from (its navigation entry), or null. */
export function loadedDocumentUrl(): string | null {
  const entries = typeof performance.getEntriesByType === "function" ? performance.getEntriesByType("navigation") : [];
  return entries[0]?.name ?? null;
}

/** The query parameter that reopens a channel's connect dialog after a reload. */
const RESUME_PARAM = "facebook";

/** The same page loaded again, opening `kind`'s connect dialog. */
export function resumeAddress(href: string, kind: MetaChannel): string {
  const url = new URL(href);
  url.searchParams.set(RESUME_PARAM, kind);
  return `${url.pathname}${url.search}${url.hash}`;
}

/** The channel a reloaded page should open the dialog of, if any. */
export function resumedChannel(search: string): MetaChannel | null {
  const kind = new URLSearchParams(search).get(RESUME_PARAM);
  return kind === "whatsapp" || kind === "instagram" || kind === "messenger" ? kind : null;
}

/** The address without the resume parameter (shown once, then removed). */
export function withoutResume(href: string): string {
  const url = new URL(href);
  url.searchParams.delete(RESUME_PARAM);
  return `${url.pathname}${url.search}${url.hash}`;
}
