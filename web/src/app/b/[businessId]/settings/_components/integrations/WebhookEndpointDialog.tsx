"use client";

import { useState, type FormEvent } from "react";

import { describeError } from "@/api/errors";
import { Alert, Button, Checkbox, Field, Fieldset, Input, Modal } from "@/components/ui";
import { useI18n } from "@/i18n/client";
import {
  eventLabelKey,
  type BusinessEventType,
  type CreatedWebhookEndpoint,
  type WebhookEndpointView,
} from "@/lib/apiIntegrations";

import { WEBHOOK_REASONS, type useWebhooks } from "../../_lib/useWebhooks";

type Draft = { url: string; label: string; events: BusinessEventType[] };

function draftOf(endpoint: WebhookEndpointView | null): Draft {
  return { url: endpoint?.url ?? "", label: endpoint?.label ?? "", events: endpoint ? [...endpoint.event_types] : [] };
}

/**
 * Adds a webhook or edits one: its https address, a name for the owner and
 * the events it receives. A new one's signing secret goes to `onCreated`.
 */
export function WebhookEndpointDialog({
  open,
  endpoint,
  eventTypes,
  webhooks,
  onClose,
  onCreated,
}: {
  open: boolean;
  endpoint: WebhookEndpointView | null;
  eventTypes: readonly BusinessEventType[];
  webhooks: ReturnType<typeof useWebhooks>;
  onClose: () => void;
  onCreated: (created: CreatedWebhookEndpoint) => void;
}) {
  const { t, tp } = useI18n();
  const [draft, setDraft] = useState<Draft>(() => draftOf(endpoint));
  const [error, setError] = useState<unknown>(null);
  const [eventsMissing, setEventsMissing] = useState(false);

  const toggle = (eventType: BusinessEventType, checked: boolean) => {
    setEventsMissing(false);
    setDraft((current) => ({
      ...current,
      events: checked ? [...current.events, eventType] : current.events.filter((item) => item !== eventType),
    }));
  };

  const submit = async (event: FormEvent) => {
    event.preventDefault();
    if (draft.events.length === 0) {
      setEventsMissing(true);
      return;
    }
    const events = eventTypes.filter((eventType) => draft.events.includes(eventType));
    const label = draft.label.trim() || null;
    setError(null);
    if (endpoint) {
      const result = await webhooks.updateEndpoint(endpoint, { url: draft.url.trim(), label, event_types: events });
      if (result.ok) onClose();
      else setError(result.error);
      return;
    }
    const result = await webhooks.createEndpoint({ url: draft.url.trim(), label, event_types: events });
    if (result.ok) onCreated(result.data);
    else setError(result.error);
  };

  const formId = endpoint ? `webhook-${endpoint.id}` : "webhook-new";
  return (
    <Modal
      open={open}
      onClose={onClose}
      title={t(endpoint ? "apiIntegrations.webhooks.dialog.editTitle" : "apiIntegrations.webhooks.dialog.addTitle")}
      footer={
        <>
          <Button variant="secondary" onClick={onClose}>
            {t("common.cancel")}
          </Button>
          <Button type="submit" form={formId} isLoading={webhooks.isSaving}>
            {t(endpoint ? "apiIntegrations.webhooks.dialog.save" : "apiIntegrations.webhooks.dialog.create")}
          </Button>
        </>
      }
    >
      <form id={formId} onSubmit={submit} className="space-y-5" noValidate>
        {error ? <Alert tone="danger">{describeError(error, { t, tp }, undefined, WEBHOOK_REASONS).title}</Alert> : null}
        <Field label={t("apiIntegrations.webhooks.dialog.url")} hint={t("apiIntegrations.webhooks.dialog.urlHint")} required>
          {(control) => (
            <Input
              {...control}
              type="url"
              dir="ltr"
              inputMode="url"
              autoComplete="off"
              placeholder="https://"
              value={draft.url}
              onChange={(event) => setDraft((current) => ({ ...current, url: event.target.value }))}
            />
          )}
        </Field>
        <Field label={t("apiIntegrations.webhooks.dialog.label")} hint={t("apiIntegrations.webhooks.dialog.labelHint")} optionalLabel={t("common.optional")}>
          {(control) => (
            <Input
              {...control}
              maxLength={80}
              value={draft.label}
              onChange={(event) => setDraft((current) => ({ ...current, label: event.target.value }))}
            />
          )}
        </Field>
        <Fieldset
          legend={t("apiIntegrations.webhooks.dialog.events")}
          hint={t("apiIntegrations.webhooks.dialog.eventsHint")}
          error={eventsMissing ? t("apiIntegrations.webhooks.dialog.eventsMissing") : undefined}
        >
          <div className="grid gap-3 sm:grid-cols-2">
            {eventTypes.map((eventType) => (
              <Checkbox
                key={eventType}
                label={t(eventLabelKey(eventType))}
                checked={draft.events.includes(eventType)}
                onChange={(event) => toggle(eventType, event.target.checked)}
              />
            ))}
          </div>
        </Fieldset>
      </form>
    </Modal>
  );
}
