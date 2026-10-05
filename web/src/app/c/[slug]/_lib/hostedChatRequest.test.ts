import { beforeEach, describe, expect, it, vi } from "vitest";

import { encodeLookup, type HostedChatView } from "@/server/hostedChat";

import { chatLanguage, readHostedChatRequest, visitorLanguage } from "./hostedChatRequest";

const { incoming } = vi.hoisted(() => ({ incoming: new Headers() }));

vi.mock("next/headers", () => ({ headers: async () => incoming }));

const VIEW: HostedChatView = {
  business_id: "business_1",
  slug: "cafe",
  business_name: "Cafe",
  is_enabled: true,
  default_language: "ka",
  languages: [
    { tag: "ka", native_name: "ქართული", direction: "ltr" },
    { tag: "ar", native_name: "العربية", direction: "rtl" },
  ],  conversation_retention_days: 730,
  llm_turn_retention_days: 30,
};

beforeEach(() => {
  for (const name of [...incoming.keys()]) {
    incoming.delete(name);
  }
});

describe("the hosted chat page's request", () => {
  it("reads what the proxy handed over", async () => {
    incoming.set("x-aw-hosted-chat", encodeLookup({ kind: "found", view: VIEW }));
    incoming.set("x-nonce", "abc");
    incoming.set("accept-language", "ar-EG,ar;q=0.9");

    expect(await readHostedChatRequest()).toEqual({
      lookup: { kind: "found", view: VIEW },
      acceptLanguage: "ar-EG,ar;q=0.9",
      nonce: "abc",
    });
  });

  it("treats a page reached without the proxy as failed", async () => {
    expect(await readHostedChatRequest()).toEqual({ lookup: { kind: "failed" }, acceptLanguage: null, nonce: undefined });
  });

  it("speaks the visitor's language among the business's, else its default one", () => {
    expect(chatLanguage(VIEW, "ar-EG")).toEqual({ language: "ar", direction: "rtl" });
    expect(chatLanguage(VIEW, "de-DE")).toEqual({ language: "ka", direction: "ltr" });
    expect(chatLanguage({ ...VIEW, languages: [] }, "he")).toEqual({ language: "ka", direction: "ltr" });
  });

  it("without a business, speaks the visitor's language among the page's texts", () => {
    expect(visitorLanguage("he-IL,en;q=0.5")).toEqual({ language: "he", direction: "rtl" });
    expect(visitorLanguage("sw")).toEqual({ language: "en", direction: "ltr" });
  });
});
