import { describe, expect, it } from "vitest";

import type { BusinessView, CurrentUserView } from "@/api/types";
import { BusinessProvider } from "@/components/business/BusinessContext";
import type { MessageView } from "@/components/insights/types";
import { renderInLocale, textsIn } from "@/test/render";

import { ConversationTechnicalDetails, hasTechnicalDetails, MessageTechnicalDetails } from "./TechnicalDetails";

const business = { id: "business_1", viewer_role: "owner", status: "live", currency_code: "EUR", timezone: "Europe/Rome" } as unknown as BusinessView;
const VERSION_ID = "0b6f2d4e-7a1c-4c3e-9f55-2f1d7e8a9b10";

const message = {
  id: "message_1",
  model_id: "model-x",
  input_tokens: 120,
  output_tokens: 30,
  cost_micro_usd: 40,
  tool_calls: [{ tool_name: "check_availability", input_json: '{"date":"2026-11-07"}', result_json: '{"slots":[]}', is_error: false }],
} as unknown as MessageView;

function show(isPlatformAdmin: boolean) {
  const me = { user: { id: "user_1", is_platform_admin: isPlatformAdmin } } as unknown as CurrentUserView;
  return renderInLocale(
    <BusinessProvider business={business} me={me}>
      <MessageTechnicalDetails message={message} />
      <ConversationTechnicalDetails totals={{ inputTokens: 120, outputTokens: 30, costMicroUsd: 40 }} versionId={VERSION_ID} />
    </BusinessProvider>,
  );
}

describe("technical details in the inbox", () => {
  const { t } = textsIn("en");

  it("are not shown to owners and staff: no raw tool JSON, no version id", () => {
    const { container } = show(false);

    expect(hasTechnicalDetails(message, false)).toBe(false);
    expect(container.textContent).toBe("");
    expect(container.querySelector("details")).toBeNull();
  });

  it("show platform admins the tool calls, the version and the usage", () => {
    const { container } = show(true);

    expect(hasTechnicalDetails(message, true)).toBe(true);
    expect(hasTechnicalDetails({ ...message, tool_calls: [], model_id: null, input_tokens: 0 } as MessageView, true)).toBe(false);
    expect(container.querySelectorAll("details")).toHaveLength(2);
    expect(container.textContent).toContain(t("inboxCard.technical.title"));
    expect(container.textContent).toContain("check_availability");
    expect(container.textContent).toContain(VERSION_ID);
  });
});
