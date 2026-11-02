import { describe, expect, it } from "vitest";

import { HOSTED_CHAT_LANGUAGES } from "@/lib/hostedChat/texts";

import {
  CUSTOMER_PAGE_LINK_LANGUAGES,
  accessibilityStatementPath,
  customerPageLinkNames,
  privacyNoticeOfChat,
} from "./customerPageLinks";

describe("the links at the foot of customers' pages", () => {
  it("are named in every language of the chat page", () => {
    expect([...CUSTOMER_PAGE_LINK_LANGUAGES].sort()).toEqual([...HOSTED_CHAT_LANGUAGES].sort());
    for (const language of CUSTOMER_PAGE_LINK_LANGUAGES) {
      const names = customerPageLinkNames(language);
      expect(names.language).toBe(language);
      expect(names.privacy.trim()).not.toBe("");
      expect(names.accessibility.trim()).not.toBe("");
    }
    expect(customerPageLinkNames("it-IT")).toEqual({ privacy: "Informativa privacy", accessibility: "Accessibilità", language: "it" });
    // A language without names: English, marked as such.
    expect(customerPageLinkNames("sw")).toEqual({ privacy: "Privacy notice", accessibility: "Accessibility", language: "en" });
  });

  it("lead to the accessibility statement in the page's language when the site has it", () => {
    expect(accessibilityStatementPath("it")).toBe("/it/accessibility");
    expect(accessibilityStatementPath("en-GB")).toBe("/en/accessibility");
    expect(accessibilityStatementPath("ka")).toBe("/en/accessibility");
  });

  it("find the business's privacy notice from its chat link", () => {
    expect(privacyNoticeOfChat("https://app.example.com/c/cafe-roma")).toBe("https://app.example.com/c/cafe-roma/privacy");
    expect(privacyNoticeOfChat("https://app.example.com/c/cafe-roma?src=booking")).toBe("https://app.example.com/c/cafe-roma/privacy");
    expect(privacyNoticeOfChat("https://wa.me/39333")).toBeNull();
    expect(privacyNoticeOfChat("tel:+39333")).toBeNull();
    expect(privacyNoticeOfChat("not a link")).toBeNull();
  });
});
