import "server-only";

import { headers } from "next/headers";

import { chooseLanguage, directionOf } from "@/lib/hostedChat/language";
import { HOSTED_CHAT_LANGUAGES } from "@/lib/hostedChat/texts";
import { NONCE_HEADER } from "@/server/contentSecurityPolicy";
import { HOSTED_CHAT_HEADER, decodeLookup, type HostedChatLookup, type HostedChatView } from "@/server/hostedChat";

export interface HostedChatRequest {
  /** What the proxy learned about the address (server/hostedChatProxy.ts). */
  lookup: HostedChatLookup;
  acceptLanguage: string | null;
  /** The page's script nonce (the widget script needs it). */
  nonce: string | undefined;
}

export interface PageLanguage {
  language: string;
  direction: "ltr" | "rtl";
}

export async function readHostedChatRequest(): Promise<HostedChatRequest> {
  const incoming = await headers();
  return {
    lookup: decodeLookup(incoming.get(HOSTED_CHAT_HEADER)),
    acceptLanguage: incoming.get("accept-language"),
    nonce: incoming.get(NONCE_HEADER) ?? undefined,
  };
}

/** The visitor's language among the business's customer languages, else its default one. */
export function chatLanguage(view: HostedChatView, acceptLanguage: string | null): PageLanguage {
  const tags = view.languages.map((language) => language.tag);
  const language = chooseLanguage(acceptLanguage, tags, view.default_language);
  const direction = view.languages.find((entry) => entry.tag === language)?.direction;
  return { language, direction: direction === "rtl" || direction === "ltr" ? direction : directionOf(language) };
}

/** Without a business (not found, API down): the visitor's language among the page's texts. */
export function visitorLanguage(acceptLanguage: string | null): PageLanguage {
  const language = chooseLanguage(acceptLanguage, HOSTED_CHAT_LANGUAGES, "en");
  return { language, direction: directionOf(language) };
}
