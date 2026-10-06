import { describe, expect, it } from "vitest";

import { renderInLocale, textsIn } from "@/test/render";

import type { InboxRow } from "../../_lib/inboxModel";
import { RowPreview } from "./rowParts";

function row(overrides: Partial<InboxRow> = {}): InboxRow {
  return {
    id: "conversation-1",
    contactName: "Lukas Weber",
    contactPhone: null,
    channel: "web",
    language: "en",
    status: "open",
    isAfterHours: false,
    isSandbox: false,
    lastMessageText: "We'll get back to you soon.",
    lastMessageAttachment: null,
    lastMessageAuthor: "assistant",
    lastMessageAt: 0,
    isAssignedAutomatically: false,
    noteCount: 0,
    handoff: null,
    request: null,
    rating: null,
    ...overrides,
  };
}

describe("RowPreview", () => {
  it("clips the message on its own, in its own direction, in the Hebrew cabinet", () => {
    const { container } = renderInLocale(<RowPreview row={row()} />, { locale: "he" });
    const preview = container.querySelector<HTMLElement>("[data-clip='content']");
    const message = container.querySelector<HTMLElement>("bdi[data-user-content]");

    expect(preview?.textContent).toBe(`${textsIn("he").t("conversations.author.assistant")}: We'll get back to you soon.`);
    // The English text is isolated and truncated by itself, so its first
    // words stay visible and the ellipsis lands at its own end.
    expect(message?.textContent).toBe("We'll get back to you soon.");
    expect(message?.className).toContain("truncate");
    expect(preview?.firstElementChild?.className).toContain("shrink-0");
  });

  it("names the media when a message has no text", () => {
    const { container } = renderInLocale(
      <RowPreview row={row({ lastMessageText: null, lastMessageAttachment: "audio", lastMessageAuthor: "customer" })} />,
    );
    expect(container.textContent).toBe(textsIn("en").t("conversationMedia.kinds.audio"));
    expect(container.querySelector("bdi")).toBeNull();
  });
});
