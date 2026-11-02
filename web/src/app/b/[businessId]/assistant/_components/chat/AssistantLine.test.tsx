import { screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";

import type { BusinessView, CurrentUserView } from "@/api/types";
import { BusinessProvider } from "@/components/business/BusinessContext";
import { renderInLocale, textsIn } from "@/test/render";

import type { ChatEntry } from "../../_lib/chatEntries";
import { AssistantLine } from "./AssistantLine";

const business = { id: "business_1", viewer_role: "owner", status: "live", currency_code: "EUR" } as unknown as BusinessView;

function viewer(isPlatformAdmin: boolean): CurrentUserView {
  return { user: { id: "user_1", is_platform_admin: isPlatformAdmin } } as unknown as CurrentUserView;
}

const entry: Extract<ChatEntry, { kind: "assistant" }> = {
  kind: "assistant",
  key: "a",
  text: "Prenotato per sabato alle 20:00.",
  versionId: null,
  reply: { created_booking_ids: ["booking_1"] } as never,
  toolCalls: [{ tool_name: "create_booking", input_json: '{"party_size":2}', result_json: '{"ok":true}', is_error: false }] as never,
};

function show(isPlatformAdmin: boolean | null) {
  const line = <AssistantLine entry={entry} answerLabel={() => ""} />;
  return renderInLocale(
    isPlatformAdmin === null ? (
      line
    ) : (
      <BusinessProvider business={business} me={viewer(isPlatformAdmin)}>
        {line}
      </BusinessProvider>
    ),
  );
}

describe("AssistantLine in the test chat", () => {
  const { t, tp } = textsIn("en");

  it.each([false, null])("shows owners what the assistant did in plain words, not raw tool calls (admin: %s)", (isPlatformAdmin) => {
    const { container } = show(isPlatformAdmin);

    expect(screen.getByText(tp("assistant.chat.bookingsCreated", 1))).toBeTruthy();
    expect(screen.queryByText(tp("assistant.chat.toolCalls", 1))).toBeNull();
    expect(container.textContent).not.toContain("create_booking");
    expect(container.textContent).not.toContain("party_size");
  });

  it("folds the raw tool calls for platform admins", () => {
    show(true);

    expect(screen.getByText(tp("assistant.chat.toolCalls", 1))).toBeTruthy();
    expect(screen.getByText("create_booking")).toBeTruthy();
    expect(screen.getByText(t("assistant.chat.toolInput"))).toBeTruthy();
  });
});
