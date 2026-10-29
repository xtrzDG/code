import { describe, expect, it } from "vitest";

import { isMetaSignInPage } from "./metaSignInPages";

describe("the pages where an owner signs in with Facebook", () => {
  it("are the Channels page and the setup tunnel of a business", () => {
    expect(isMetaSignInPage("/b/business_1/assistant/channels")).toBe(true);
    expect(isMetaSignInPage("/b/business_1/assistant/channels/")).toBe(true);
    expect(isMetaSignInPage("/b/business_1/setup")).toBe(true);
  });

  it("are no other page, not even the Channels page's own pages", () => {
    expect(isMetaSignInPage("/b/business_1/assistant/channels/website")).toBe(false);
    expect(isMetaSignInPage("/b/business_1/overview")).toBe(false);
    expect(isMetaSignInPage("/login")).toBe(false);
    expect(isMetaSignInPage("/c/cafe/assistant/channels")).toBe(false);
    expect(isMetaSignInPage("/b//setup")).toBe(false);
  });
});
