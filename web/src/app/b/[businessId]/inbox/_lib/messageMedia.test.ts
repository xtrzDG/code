import { describe, expect, it } from "vitest";

import { en } from "@/i18n/messages/en";
import { ka } from "@/i18n/messages/ka";
import { ru } from "@/i18n/messages/ru";
import { lookupMessage, type MessageTree } from "@/i18n/translate";

import {
  ATTACHMENT_KIND_LABELS,
  ATTACHMENT_PROBLEMS,
  formatCoordinates,
  hasStoredFile,
  messageAttachments,
  messageMediaUrl,
  placeSubtitle,
  placeTitle,
  safeMapUrl,
  voiceDuration,
  voiceTranscript,
  type MessageAttachmentView,
} from "./messageMedia";

function attachment(overrides: Partial<MessageAttachmentView>): MessageAttachmentView {
  return { kind: "audio", is_media_deleted: false, ...overrides };
}

describe("customer media in the cabinet", () => {
  it("loads a file through the BFF, with the ids escaped", () => {
    expect(messageMediaUrl("business_1", "media_2")).toBe("/api/backend/v1/businesses/business_1/media/media_2");
    expect(messageMediaUrl("b/1", "m?2")).toBe("/api/backend/v1/businesses/b%2F1/media/m%3F2");
  });

  it("plays and shows only files that are still kept", () => {
    expect(hasStoredFile(attachment({ media_id: "media_1" }))).toBe(true);
    expect(hasStoredFile(attachment({ media_id: "media_1", is_media_deleted: true }))).toBe(false);
    expect(hasStoredFile(attachment({ media_id: null }))).toBe(false);
    expect(hasStoredFile(attachment({}))).toBe(false);
  });

  it("tells the length and the words of a voice message", () => {
    expect(voiceDuration(attachment({ duration_seconds: 7 }))).toBe("0:07");
    expect(voiceDuration(attachment({ duration_seconds: 95 }))).toBe("1:35");
    expect(voiceDuration(attachment({ duration_seconds: null }))).toBeNull();
    expect(voiceDuration(attachment({}))).toBeNull();
    expect(voiceTranscript(attachment({ transcript: "  Hello  " }))).toBe("Hello");
    expect(voiceTranscript(attachment({ transcript: "   " }))).toBeNull();
    expect(voiceTranscript(attachment({ transcript: null }))).toBeNull();
  });

  it("describes a place by its name, then its address, then nothing", () => {
    const square = { latitude: 41.693438, longitude: 44.801525, name: "Freedom Square", address: "Tbilisi" };
    expect(formatCoordinates(square)).toBe("41.69344, 44.80152");
    expect(formatCoordinates({ latitude: -33.8688, longitude: 151.2093 })).toBe("-33.86880, 151.20930");
    expect(placeTitle(square)).toBe("Freedom Square");
    expect(placeSubtitle(square)).toBe("Tbilisi");
    expect(placeTitle({ ...square, name: " " })).toBe("Tbilisi");
    expect(placeSubtitle({ ...square, name: null })).toBeNull();
    expect(placeSubtitle({ ...square, address: "Freedom Square" })).toBeNull();
    expect(placeTitle({ latitude: 1, longitude: 2 })).toBeNull();
  });

  it("links only to web addresses", () => {
    expect(safeMapUrl("https://maps.google.com/?q=41.693438,44.801525")).toBe("https://maps.google.com/?q=41.693438,44.801525");
    expect(safeMapUrl("http://maps.example/x")).toBe("http://maps.example/x");
    expect(safeMapUrl("javascript:alert(1)")).toBeNull();
    expect(safeMapUrl("data:text/html,hi")).toBeNull();
    expect(safeMapUrl("not a url")).toBeNull();
    expect(safeMapUrl(null)).toBeNull();
    expect(safeMapUrl(undefined)).toBeNull();
  });

  it("reads a message without attachments as none", () => {
    expect(messageAttachments({})).toEqual([]);
    expect(messageAttachments({ attachments: null })).toEqual([]);
    const voice = attachment({ transcript: "Hi" });
    expect(messageAttachments({ attachments: [voice] })).toEqual([voice]);
  });

  it("names every kind and every problem in English, Russian and Georgian", () => {
    for (const messages of [en, ru, ka] as unknown as MessageTree[]) {
      for (const key of [...Object.values(ATTACHMENT_KIND_LABELS), ...Object.values(ATTACHMENT_PROBLEMS)]) {
        const text = lookupMessage(messages, key);
        expect(typeof text).toBe("string");
        expect(String(text).length).toBeGreaterThan(2);
      }
    }
    expect(lookupMessage(en as unknown as MessageTree, ATTACHMENT_KIND_LABELS.other)).toBe("File");
  });
});
