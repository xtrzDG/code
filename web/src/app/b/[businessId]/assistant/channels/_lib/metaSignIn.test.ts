import { describe, expect, it } from "vitest";

import {
  completeSignupBody,
  documentAllowsFacebook,
  facebookLoginOptions,
  isMetaChannel,
  loadedDocumentUrl,
  offersFacebook,
  pageTitle,
  purposeOf,
  readSignupMessage,
  resumeAddress,
  resumedChannel,
  withoutResume,
  type MetaSignInStart,
} from "./metaSignIn";

const FINISH = JSON.stringify({
  type: "WA_EMBEDDED_SIGNUP",
  event: "FINISH",
  data: { phone_number_id: "106540352242923", waba_id: "102290129340398" },
});

const start = (purpose: "whatsapp" | "pages"): MetaSignInStart => ({
  purpose,
  state: "s".repeat(43),
  app_id: "1234567890",
  graph_api_version: "v23.0",
  configuration_id: purpose === "whatsapp" ? "987654321" : null,
  permissions: purpose === "pages" ? ["pages_show_list", "pages_messaging"] : [],
  expires_at: 0,
});

describe("which sign-in a channel uses", () => {
  it("is Embedded Signup for WhatsApp and the page picker for Instagram and Messenger", () => {
    expect(purposeOf("whatsapp")).toBe("whatsapp");
    expect(purposeOf("instagram")).toBe("pages");
    expect(purposeOf("messenger")).toBe("pages");
    expect(isMetaChannel("instagram")).toBe(true);
    expect(isMetaChannel("telegram")).toBe(false);
    expect(isMetaChannel(null)).toBe(false);
  });

  it("is offered only when the server has the app (and, for WhatsApp, its signup)", () => {
    const options = { whatsapp: false, pages: true, app_id: "1234567890", graph_api_version: "v23.0" };

    expect(offersFacebook(options, "messenger")).toBe(true);
    expect(offersFacebook(options, "whatsapp")).toBe(false);
    expect(offersFacebook({ ...options, app_id: null }, "messenger")).toBe(false);
    expect(offersFacebook(undefined, "instagram")).toBe(false);
  });
});

describe("what Facebook's window opens with", () => {
  it("asks for a code: the signup configuration, or the page picker's permissions", () => {
    expect(facebookLoginOptions(start("whatsapp"))).toEqual({
      config_id: "987654321",
      response_type: "code",
      override_default_response_type: true,
      extras: { setup: {}, featureType: "", sessionInfoVersion: "3" },
    });
    expect(facebookLoginOptions(start("pages"))).toMatchObject({
      scope: "pages_show_list,pages_messaging",
      response_type: "code",
      auth_type: "rerequest",
    });
  });
});

describe("the messages of WhatsApp's signup window", () => {
  it("are read only from Facebook's own origins", () => {
    expect(readSignupMessage("https://www.facebook.com", FINISH)).toEqual({
      event: "finish",
      businessAccountId: "102290129340398",
      phoneNumberId: "106540352242923",
    });
    expect(readSignupMessage("https://web.facebook.com", JSON.parse(FINISH))).toMatchObject({ event: "finish" });
    for (const origin of ["https://evilfacebook.com", "https://www.facebook.com.example", "http://www.facebook.com", "null"]) {
      expect(readSignupMessage(origin, FINISH)).toBeNull();
    }
  });

  it("keep only numeric ids and known events", () => {
    const odd = JSON.stringify({ type: "WA_EMBEDDED_SIGNUP", event: "FINISH_ONLY_WABA", data: { waba_id: "<b>", phone_number_id: 7 } });

    expect(readSignupMessage("https://www.facebook.com", odd)).toEqual({
      event: "finish",
      businessAccountId: null,
      phoneNumberId: null,
    });
    expect(readSignupMessage("https://www.facebook.com", JSON.stringify({ type: "WA_EMBEDDED_SIGNUP", event: "CANCEL", data: { current_step: "PHONE_NUMBER" } }))).toEqual({ event: "cancel" });
    expect(readSignupMessage("https://www.facebook.com", JSON.stringify({ type: "WA_EMBEDDED_SIGNUP", event: "ERROR" }))).toEqual({ event: "error" });
    expect(readSignupMessage("https://www.facebook.com", JSON.stringify({ type: "WA_EMBEDDED_SIGNUP", event: "SOMETHING" }))).toBeNull();
    expect(readSignupMessage("https://www.facebook.com", JSON.stringify({ type: "OTHER", event: "FINISH" }))).toBeNull();
    expect(readSignupMessage("https://www.facebook.com", "not json")).toBeNull();
    expect(readSignupMessage("https://www.facebook.com", "x".repeat(10_001))).toBeNull();
    expect(readSignupMessage("https://www.facebook.com", ["FINISH"])).toBeNull();
  });

  it("add the reported ids to the body that finishes the signup", () => {
    const session = readSignupMessage("https://www.facebook.com", FINISH);

    expect(completeSignupBody("state", "AQB-code", session)).toEqual({
      state: "state",
      code: "AQB-code",
      whatsapp_business_account_id: "102290129340398",
      phone_number_id: "106540352242923",
    });
    expect(completeSignupBody("state", "AQB-code", { event: "cancel" })).toEqual({ state: "state", code: "AQB-code" });
    expect(completeSignupBody("state", "AQB-code", null)).toEqual({ state: "state", code: "AQB-code" });
  });
});

describe("a page's title", () => {
  it("is its name, else its username, else its id", () => {
    const page = { page_id: "4410001", has_instagram: false };
    expect(pageTitle({ ...page, name: "Cafe Ezo", username: "cafe.ezo" })).toBe("Cafe Ezo");
    expect(pageTitle({ ...page, name: "  ", username: "cafe.ezo" })).toBe("cafe.ezo");
    expect(pageTitle(page)).toBe("4410001");
  });
});

describe("whether this document may open Facebook", () => {
  it("depends on the page it was loaded as", () => {
    expect(documentAllowsFacebook("https://cabinet.example/b/business_1/assistant/channels?x=1")).toBe(true);
    expect(documentAllowsFacebook("https://cabinet.example/b/business_1/setup")).toBe(true);
    expect(documentAllowsFacebook("https://cabinet.example/b/business_1/overview")).toBe(false);
    expect(documentAllowsFacebook("not a url")).toBe(false);
    // No navigation entry (very old browsers): no reload loop.
    expect(documentAllowsFacebook(null)).toBe(true);
    expect(loadedDocumentUrl()).toBeNull();
  });

  it("reopens the dialog of the channel named in the address, once", () => {
    const address = resumeAddress("https://cabinet.example/b/business_1/setup?step=channels#top", "instagram");

    expect(address).toBe("/b/business_1/setup?step=channels&facebook=instagram#top");
    expect(resumedChannel("?step=channels&facebook=instagram")).toBe("instagram");
    expect(resumedChannel("?facebook=telegram")).toBeNull();
    expect(resumedChannel("")).toBeNull();
    expect(withoutResume(`https://cabinet.example${address}`)).toBe("/b/business_1/setup?step=channels#top");
  });
});
