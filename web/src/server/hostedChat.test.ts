import { afterEach, describe, expect, it, vi } from "vitest";

import {
  chatApiBase,
  decodeLookup,
  encodeLookup,
  hostedChatAddress,
  hostedChatPath,
  isHostedChatPath,
  lookUpHostedChat,
  originOf,
  type HostedChatView,
} from "./hostedChat";

const HOSTED_VIEW: HostedChatView = {
  business_id: "business_0b6c2f5e-1d1a-4c55-9a3e-2f1d5b7c9e01",
  slug: "mtsvane-ezo",
  business_name: "მწვანე ეზო — Café",
  is_enabled: true,
  default_language: "ka",
  languages: [
    { tag: "ka", native_name: "ქართული", direction: "ltr" },
    { tag: "he", native_name: "עברית", direction: "rtl" },
  ],
  accent_color: "#AD5732",
  api_base_url: "https://api.workshop.example",
  widget_script_url: "https://api.workshop.example/widget.js",
  privacy_url: null,  conversation_retention_days: 730,
  llm_turn_retention_days: 30,
  takes_bookings: false,
};

afterEach(() => {
  vi.unstubAllGlobals();
});

describe("hosted chat addresses", () => {
  it("takes the address of /c/{address} only", () => {
    expect(hostedChatAddress("/c/mtsvane-ezo")).toBe("mtsvane-ezo");
    expect(hostedChatAddress("/c/mtsvane-ezo/")).toBe("mtsvane-ezo");
    expect(hostedChatAddress("/c/business_0b6c2f5e-1d1a")).toBe("business_0b6c2f5e-1d1a");
    expect(hostedChatAddress("/c/mtsvane-ezo/privacy")).toBeNull();
    expect(hostedChatAddress("/c/")).toBeNull();
    expect(hostedChatAddress("/c/%2e%2e")).toBeNull();
    expect(hostedChatAddress("/b/x")).toBeNull();
    expect(isHostedChatPath("/c/x/privacy")).toBe(true);
    expect(isHostedChatPath("/cabinet")).toBe(false);
    expect(hostedChatPath("new-name", "?src=qr")).toBe("/c/new-name?src=qr");
  });
});

describe("the lookup the proxy hands to the page", () => {
  it("survives the header in UTF-8", () => {
    const encoded = encodeLookup({ kind: "found", view: HOSTED_VIEW });
    expect(encoded).toMatch(/^v1\.[A-Za-z0-9_-]+$/);
    expect(decodeLookup(encoded)).toEqual({ kind: "found", view: HOSTED_VIEW });
  });

  it("says when there is no business or the API failed", () => {
    expect(decodeLookup(encodeLookup({ kind: "missing" }))).toEqual({ kind: "missing" });
    expect(decodeLookup(encodeLookup({ kind: "failed" }))).toEqual({ kind: "failed" });
    expect(decodeLookup(null)).toEqual({ kind: "failed" });
    expect(decodeLookup("v1.not*base64")).toEqual({ kind: "failed" });
    expect(decodeLookup(`v1.${btoa("{}")}`)).toEqual({ kind: "failed" });
  });
});

describe("where the browser reaches the API", () => {
  it("uses APP_BASE_URL from the API, else BACKEND_URL", () => {
    expect(chatApiBase(HOSTED_VIEW)).toBe("https://api.workshop.example");
    expect(chatApiBase({ ...HOSTED_VIEW, api_base_url: null }, { BACKEND_URL: "http://localhost:8852/" })).toBe(
      "http://localhost:8852",
    );
    expect(originOf("https://api.workshop.example/v1")).toBe("https://api.workshop.example");
    expect(originOf("javascript:alert(1)")).toBeNull();
    expect(originOf("not a url")).toBeNull();
  });
});

describe("lookUpHostedChat", () => {
  it("returns the view, a missing business or a failure", async () => {
    const fetchMock = vi.fn(async (url: string) =>
      url.endsWith("/mtsvane-ezo")
        ? Response.json(HOSTED_VIEW)
        : url.endsWith("/nobody")
          ? Response.json({ error: "not_found" }, { status: 404 })
          : new Response("", { status: 503 }),
    );
    vi.stubGlobal("fetch", fetchMock);

    expect(await lookUpHostedChat("mtsvane-ezo", new Headers({ "accept-language": "ka" }))).toEqual({
      kind: "found",
      view: HOSTED_VIEW,
    });
    expect(await lookUpHostedChat("nobody", null)).toEqual({ kind: "missing" });
    expect(await lookUpHostedChat("broken", null)).toEqual({ kind: "failed" });
    expect(fetchMock.mock.calls[0]?.[0]).toMatch(/\/v1\/public\/chat\/mtsvane-ezo$/);

    vi.stubGlobal("fetch", vi.fn().mockRejectedValue(new Error("down")));
    expect(await lookUpHostedChat("mtsvane-ezo", null)).toEqual({ kind: "failed" });
  });
});
