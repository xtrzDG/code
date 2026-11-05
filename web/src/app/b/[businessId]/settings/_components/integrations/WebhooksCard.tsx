"use client";

import { useState } from "react";

import { IconPlus, IconSend } from "@/components/icons";
import { Button, Card, ConfirmDialog, EmptyState, ErrorState, SkeletonRows, useToast } from "@/components/ui";
import { useI18n } from "@/i18n/client";
import type { WebhookEndpointView } from "@/lib/apiIntegrations";

import { useWebhooks } from "../../_lib/useWebhooks";
import { SecretRevealDialog, type RevealedSecret } from "./SecretRevealDialog";
import { WebhookDeliveriesDrawer } from "./WebhookDeliveriesDrawer";
import { WebhookEndpointDialog } from "./WebhookEndpointDialog";
import { WebhookRow, type WebhookAction } from "./WebhookRow";

type Editing = { open: boolean; endpoint: WebhookEndpointView | null; nonce: number };
type Confirming = { action: "delete" | "rotate"; endpoint: WebhookEndpointView } | null;

/**
 * Outbound webhooks: the addresses the business's events go to, a dialog
 * to add or edit one, its signing secret shown once, "Send test event",
 * pause and resume, and the delivery log of each.
 */
export function WebhooksCard() {
  const { t, tp } = useI18n();
  const toast = useToast();
  const webhooks = useWebhooks();
  const [editing, setEditing] = useState<Editing>({ open: false, endpoint: null, nonce: 0 });
  const [confirming, setConfirming] = useState<Confirming>(null);
  const [secret, setSecret] = useState<RevealedSecret | null>(null);
  const [logOf, setLogOf] = useState<WebhookEndpointView | null>(null);
  const data = webhooks.list.data;

  const openEditor = (endpoint: WebhookEndpointView | null) =>
    setEditing((current) => ({ open: true, endpoint, nonce: current.nonce + 1 }));
  const closeEditor = () => setEditing((current) => ({ ...current, open: false }));

  const onAction = async (action: WebhookAction, endpoint: WebhookEndpointView) => {
    if (action === "edit") openEditor(endpoint);
    if (action === "deliveries") setLogOf(endpoint);
    if (action === "delete" || action === "rotate") setConfirming({ action, endpoint });
    if (action === "pause" || action === "resume") {
      const result = await webhooks.updateEndpoint(endpoint, { status: action === "pause" ? "paused" : "active" });
      if (result.ok) toast.success(t(action === "pause" ? "apiIntegrations.webhooks.toasts.paused" : "apiIntegrations.webhooks.toasts.resumed"));
    }
    if (action === "test") {
      const result = await webhooks.sendTestEvent(endpoint);
      if (result.ok && result.data.status === "delivered") toast.success(t("apiIntegrations.webhooks.toasts.testDelivered"));
      else if (result.ok) toast.info(t("apiIntegrations.webhooks.toasts.testFailed"));
    }
  };

  const confirm = async () => {
    if (!confirming) return;
    if (confirming.action === "delete") {
      const result = await webhooks.deleteEndpoint(confirming.endpoint);
      if (result.ok) toast.success(t("apiIntegrations.webhooks.toasts.deleted"));
    } else {
      const result = await webhooks.rotateSecret(confirming.endpoint);
      if (result.ok) setSecret({ kind: "webhook", value: result.data.signing_secret });
    }
    setConfirming(null);
  };

  const items = data?.items ?? [];
  const full = data ? items.length >= data.max_endpoints : true;
  return (
    <Card
      padded={false}
      title={t("apiIntegrations.webhooks.title")}
      description={t("apiIntegrations.webhooks.description")}
      actions={
        <Button size="sm" leadingIcon={<IconPlus className="size-4" aria-hidden />} onClick={() => openEditor(null)} disabled={full}>
          {t("apiIntegrations.webhooks.add")}
        </Button>
      }
      footer={
        data ? (
          <p className="text-sm text-ink-subtle">
            {tp("apiIntegrations.webhooks.limits", data.max_endpoints)}{" "}
            {tp("apiIntegrations.webhooks.disableAfter", data.failures_before_disable, { failures: data.failures_before_disable })}
          </p>
        ) : undefined
      }
    >
      {webhooks.list.error && !data ? (
        <ErrorState error={webhooks.list.error} onRetry={webhooks.list.reload} className="py-6" />
      ) : !data ? (
        <SkeletonRows rows={2} className="rounded-none border-0" />
      ) : items.length === 0 ? (
        <EmptyState icon={<IconSend className="size-5" />} title={t("apiIntegrations.webhooks.empty")} />
      ) : (
        <ul className="divide-y divide-line">
          {items.map((endpoint) => (
            <WebhookRow key={endpoint.id} endpoint={endpoint} onAction={(action, row) => void onAction(action, row)} />
          ))}
        </ul>
      )}
      <WebhookEndpointDialog
        key={editing.nonce}
        open={editing.open}
        endpoint={editing.endpoint}
        eventTypes={data?.event_types ?? []}
        webhooks={webhooks}
        onClose={closeEditor}
        onCreated={(created) => {
          closeEditor();
          setSecret({ kind: "webhook", value: created.signing_secret });
        }}
      />
      <ConfirmDialog
        open={confirming !== null}
        onClose={() => setConfirming(null)}
        onConfirm={confirm}
        tone={confirming?.action === "delete" ? "danger" : "primary"}
        isPending={webhooks.isDeleting || webhooks.isRotating}
        title={t(confirming?.action === "rotate" ? "apiIntegrations.webhooks.rotateDialog.title" : "apiIntegrations.webhooks.deleteDialog.title")}
        description={
          confirming?.action === "rotate"
            ? t("apiIntegrations.webhooks.rotateDialog.description")
            : t("apiIntegrations.webhooks.deleteDialog.description", { url: confirming?.endpoint.url ?? "" })
        }
        confirmLabel={t(confirming?.action === "rotate" ? "apiIntegrations.webhooks.rotateDialog.confirm" : "apiIntegrations.webhooks.deleteDialog.confirm")}
      />
      <SecretRevealDialog secret={secret} onClose={() => setSecret(null)} />
      <WebhookDeliveriesDrawer endpoint={logOf} onClose={() => setLogOf(null)} />
    </Card>
  );
}
