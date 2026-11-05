import { describe, expect, it } from "vitest";

import { eventLabelKey, prettyPayload, scopeLabelKey } from "./apiIntegrations";

describe("apiIntegrations: names and bodies of webhooks and API keys", () => {
  it("turns event types and scopes into message keys", () => {
    expect(eventLabelKey("booking.created")).toBe("apiIntegrations.events.booking_created");
    expect(eventLabelKey("webhook.test")).toBe("apiIntegrations.events.webhook_test");
    expect(scopeLabelKey("webhooks:manage")).toBe("apiIntegrations.apiKeys.scopes.webhooks_manage");
  });

  it("indents a JSON body and keeps anything else as sent", () => {
    expect(prettyPayload('{"id":"event_1","data":{"a":1}}')).toBe('{\n  "id": "event_1",\n  "data": {\n    "a": 1\n  }\n}');
    expect(prettyPayload("not json")).toBe("not json");
  });
});
