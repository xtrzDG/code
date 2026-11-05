/**
 * Outbound webhooks and API keys (Settings → Integrations): the API's
 * shapes, how a state reads as a badge, and the message keys of events and
 * scopes (whose API names hold "." and ":", which message paths cannot).
 */

import type { RequestBody, Schema } from "@/api/types";
import type { BadgeTone } from "@/components/ui";
import type { MessageKey } from "@/i18n/translate";

export type WebhookEndpointView = Schema<"WebhookEndpointView">;
export type WebhookEndpointList = Schema<"WebhookEndpointList">;
export type CreatedWebhookEndpoint = Schema<"CreatedWebhookEndpoint">;
export type WebhookDeliveryView = Schema<"WebhookDeliveryView">;
export type BusinessEventType = Schema<"BusinessEventType">;
export type WebhookEndpointStatus = Schema<"WebhookEndpointStatus">;
export type WebhookDeliveryStatus = Schema<"WebhookDeliveryStatus">;
export type WebhookEndpointBody = RequestBody<"/v1/businesses/{business_id}/webhooks", "post">;
export type WebhookEndpointChange = RequestBody<"/v1/businesses/{business_id}/webhooks/{webhook_id}", "patch">;

export type ApiKeyView = Schema<"ApiKeyView">;
export type ApiKeyList = Schema<"ApiKeyList">;
export type CreatedApiKey = Schema<"CreatedApiKey">;
export type ApiKeyScope = Schema<"ApiKeyScope">;
export type ApiKeyBody = RequestBody<"/v1/businesses/{business_id}/api-keys", "post">;

export const ENDPOINT_TONES: Readonly<Record<WebhookEndpointStatus, BadgeTone>> = {
  active: "success",
  paused: "neutral",
  disabled: "danger",
};

export const DELIVERY_TONES: Readonly<Record<WebhookDeliveryStatus, BadgeTone>> = {
  pending: "info",
  delivered: "success",
  failed: "danger",
};

/** `booking.created` → `apiIntegrations.events.booking_created`. */
export function eventLabelKey(eventType: BusinessEventType): MessageKey {
  return `apiIntegrations.events.${eventType.replace(".", "_")}` as MessageKey;
}

/** `bookings:read` → `apiIntegrations.apiKeys.scopes.bookings_read`. */
export function scopeLabelKey(scope: ApiKeyScope): MessageKey {
  return `apiIntegrations.apiKeys.scopes.${scope.replace(":", "_")}` as MessageKey;
}

/** The delivery body for reading: indented JSON, or the text as sent. */
export function prettyPayload(payload: string): string {
  try {
    return JSON.stringify(JSON.parse(payload), null, 2);
  } catch {
    return payload;
  }
}
