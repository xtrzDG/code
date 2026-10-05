import { describe, expect, it } from "vitest";

import { en } from "@/i18n/messages/en";
import { ka } from "@/i18n/messages/ka";
import { ru } from "@/i18n/messages/ru";

import { acceptedTermsBody, splitConsentLine } from "./legalConsent";

describe("splitConsentLine", () => {
  it("keeps the words around the two documents in order", () => {
    expect(splitConsentLine("By continuing, you accept the {terms} and read the {privacy}.")).toEqual([
      { kind: "text", text: "By continuing, you accept the " },
      { kind: "document", document: "terms" },
      { kind: "text", text: " and read the " },
      { kind: "document", document: "privacy" },
      { kind: "text", text: "." },
    ]);
  });

  it("follows each language's own order and names both documents", () => {
    for (const messages of [en, ru, ka]) {
      const documents = splitConsentLine(messages.legalConsent.line)
        .filter((part) => part.kind === "document")
        .map((part) => (part.kind === "document" ? part.document : null));
      expect(documents).toEqual(["terms", "privacy"]);
    }
  });

  it("leaves a line without placeholders as one text", () => {
    expect(splitConsentLine("Plain")).toEqual([{ kind: "text", text: "Plain" }]);
  });
});

describe("acceptedTermsBody", () => {
  it("sends the version the line showed, nothing without one", () => {
    expect(acceptedTermsBody("2026-10-05")).toEqual({ accepted_terms_version: "2026-10-05" });
    expect(acceptedTermsBody(null)).toEqual({});
  });
});
