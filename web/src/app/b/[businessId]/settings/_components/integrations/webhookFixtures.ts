/** Webhooks and API keys as the API answers them, for the cards' tests. */

import type { ApiKeyList, WebhookDeliveryView, WebhookEndpointList, WebhookEndpointView } from "@/lib/apiIntegrations";

const at = (day: number) => Date.UTC(2026, 9, day, 9) * 1000;
export const SECRET = `whsec_${"0".repeat(43)}`;
export const TOKEN = `awk_aaaaaaaa_${"0".repeat(40)}`;

export function endpoint(overrides: Partial<WebhookEndpointView> = {}): WebhookEndpointView {
  return {
    id: "webhook_1",
    url: "https://crm.example.com/hooks/workshop",
    label: "CRM",
    event_types: ["booking.created", "lead.created"],
    status: "active",
    origin: "cabinet",
    secret_hint: "ab12",
    consecutive_failures: 0,
    last_success_at: at(5),
    created_at: at(1),
    ...overrides,
  };
}

export function endpointList(items: WebhookEndpointView[]): WebhookEndpointList {
  return {
    items,
    event_types: [
      "booking.created",
      "booking.updated",
      "booking.cancelled",
      "lead.created",
      "lead.updated",
      "handoff.created",
      "handoff.resolved",
      "conversation.started",
      "call.finished",
    ],
    max_endpoints: 10,
    failures_before_disable: 15,
  };
}

export function delivery(overrides: Partial<WebhookDeliveryView> = {}): WebhookDeliveryView {
  return {
    id: "webhook_delivery_1",
    endpoint_id: "webhook_1",
    event_id: "event_1",
    event_type: "booking.created",
    status: "delivered",
    is_test: false,
    attempts: 1,
    last_status_code: 200,
    created_at: at(5),
    ...overrides,
  };
}

export function apiKeyList(overrides: Partial<ApiKeyList> = {}): ApiKeyList {
  return {
    items: [
      {
        id: "api_key_1",
        name: "Zapier",
        prefix: "awk_aaaaaaaa",
        scopes: ["bookings:read", "webhooks:manage"],
        status: "active",
        created_at: at(1),
        last_used_at: at(4),
      },
      {
        id: "api_key_0",
        name: "Old script",
        prefix: "awk_bbbbbbbb",
        scopes: ["leads:write"],
        status: "revoked",
        created_at: at(1),
        revoked_at: at(2),
      },
    ],
    scopes: ["bookings:read", "bookings:write", "leads:read", "leads:write", "contacts:read", "conversations:read", "webhooks:manage"],
    max_keys: 10,
    requests_per_minute: 120,
    ...overrides,
  };
}
