"use client";

import { useState } from "react";

import { useBusinessFormat } from "@/components/business/BusinessContext";
import { IconKey, IconPlus } from "@/components/icons";
import { Badge, Button, Card, ConfirmDialog, EmptyState, ErrorState, SkeletonRows, useToast } from "@/components/ui";
import { useI18n } from "@/i18n/client";
import { scopeLabelKey, type ApiKeyView } from "@/lib/apiIntegrations";

import { useApiKeys } from "../../_lib/useApiKeys";
import { ApiKeyDialog } from "./ApiKeyDialog";
import { SecretRevealDialog, type RevealedSecret } from "./SecretRevealDialog";

function ApiKeyRow({ apiKey, onRevoke }: { apiKey: ApiKeyView; onRevoke: (apiKey: ApiKeyView) => void }) {
  const { t } = useI18n();
  const format = useBusinessFormat();
  const isActive = apiKey.status === "active";
  const used = apiKey.last_used_at
    ? t("apiIntegrations.apiKeys.lastUsed", { time: format.dateTime(apiKey.last_used_at) })
    : t("apiIntegrations.apiKeys.neverUsed");
  const facts = [
    t("apiIntegrations.apiKeys.created", { time: format.dateTime(apiKey.created_at) }),
    apiKey.revoked_at ? t("apiIntegrations.apiKeys.revokedAt", { time: format.dateTime(apiKey.revoked_at) }) : used,
  ];
  return (
    <li className="flex flex-col gap-3 px-4 py-4 sm:flex-row sm:items-start sm:gap-4 sm:px-6">
      <div className="min-w-0 flex-1 space-y-1.5">
        <div className="flex flex-wrap items-center gap-2">
          <p className="min-w-0 font-medium text-ink">{apiKey.name}</p>
          <Badge tone={isActive ? "success" : "neutral"}>{t(`apiIntegrations.apiKeys.statuses.${apiKey.status}`)}</Badge>
          <code dir="ltr" className="font-mono text-sm text-ink-muted">{`${apiKey.prefix}_…`}</code>
        </div>
        <p className="text-sm text-ink-subtle">{apiKey.scopes.map((scope) => t(scopeLabelKey(scope))).join(", ")}</p>
        <p className="text-sm text-ink-subtle">{facts.join(" · ")}</p>
      </div>
      {isActive ? (
        <Button variant="danger-ghost" size="sm" className="self-start" onClick={() => onRevoke(apiKey)}>
          {t("apiIntegrations.apiKeys.revoke")}
        </Button>
      ) : null}
    </li>
  );
}

/**
 * API keys for Zapier and the public API: create one with its scopes (the
 * token is shown once), see when each was last used, and revoke one.
 */
export function ApiKeysCard() {
  const { t } = useI18n();
  const toast = useToast();
  const apiKeys = useApiKeys();
  const [creating, setCreating] = useState({ open: false, nonce: 0 });
  const [revoking, setRevoking] = useState<ApiKeyView | null>(null);
  const [secret, setSecret] = useState<RevealedSecret | null>(null);
  const data = apiKeys.list.data;
  const items = data?.items ?? [];
  const activeCount = items.filter((item) => item.status === "active").length;

  const revoke = async () => {
    if (!revoking) return;
    const result = await apiKeys.revokeKey(revoking);
    if (result.ok) toast.success(t("apiIntegrations.apiKeys.toasts.revoked"));
    setRevoking(null);
  };

  return (
    <Card
      padded={false}
      title={t("apiIntegrations.apiKeys.title")}
      description={t("apiIntegrations.apiKeys.description")}
      actions={
        <Button
          size="sm"
          leadingIcon={<IconPlus className="size-4" aria-hidden />}
          disabled={!data || activeCount >= data.max_keys}
          onClick={() => setCreating((current) => ({ open: true, nonce: current.nonce + 1 }))}
        >
          {t("apiIntegrations.apiKeys.add")}
        </Button>
      }
      footer={
        data ? (
          <p className="text-sm text-ink-subtle">
            {t("apiIntegrations.apiKeys.limits", { count: data.max_keys, rate: data.requests_per_minute })}
          </p>
        ) : undefined
      }
    >
      {apiKeys.list.error && !data ? (
        <ErrorState error={apiKeys.list.error} onRetry={apiKeys.list.reload} className="py-6" />
      ) : !data ? (
        <SkeletonRows rows={2} className="rounded-none border-0" />
      ) : items.length === 0 ? (
        <EmptyState icon={<IconKey className="size-5" />} title={t("apiIntegrations.apiKeys.empty")} />
      ) : (
        <ul className="divide-y divide-line">
          {items.map((apiKey) => (
            <ApiKeyRow key={apiKey.id} apiKey={apiKey} onRevoke={setRevoking} />
          ))}
        </ul>
      )}
      <ApiKeyDialog
        key={creating.nonce}
        open={creating.open}
        scopes={data?.scopes ?? []}
        apiKeys={apiKeys}
        onClose={() => setCreating((current) => ({ ...current, open: false }))}
        onCreated={(created) => {
          setCreating((current) => ({ ...current, open: false }));
          setSecret({ kind: "apiKey", value: created.token });
        }}
      />
      <ConfirmDialog
        open={revoking !== null}
        onClose={() => setRevoking(null)}
        onConfirm={revoke}
        isPending={apiKeys.isRevoking}
        title={t("apiIntegrations.apiKeys.revokeDialog.title", { name: revoking?.name ?? "" })}
        description={t("apiIntegrations.apiKeys.revokeDialog.description")}
        confirmLabel={t("apiIntegrations.apiKeys.revokeDialog.confirm")}
      />
      <SecretRevealDialog secret={secret} onClose={() => setSecret(null)} />
    </Card>
  );
}
