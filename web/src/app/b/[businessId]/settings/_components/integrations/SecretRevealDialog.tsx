"use client";

import { Alert, Button, Modal } from "@/components/ui";
import { CopyButton } from "@/components/workspace/CopyButton";
import { useI18n } from "@/i18n/client";

export type RevealedSecret = { kind: "webhook" | "apiKey"; value: string };

/**
 * A secret shown once: a webhook's signing secret or a new API key. It is
 * not kept anywhere in the cabinet, so closing the dialog forgets it.
 */
export function SecretRevealDialog({ secret, onClose }: { secret: RevealedSecret | null; onClose: () => void }) {
  const { t } = useI18n();
  const isApiKey = secret?.kind === "apiKey";
  return (
    <Modal
      open={secret !== null}
      onClose={onClose}
      title={t(isApiKey ? "apiIntegrations.secret.apiKeyTitle" : "apiIntegrations.secret.webhookTitle")}
      footer={<Button onClick={onClose}>{t("apiIntegrations.secret.done")}</Button>}
    >
      <div className="space-y-4">
        <Alert tone="warning">
          {t(isApiKey ? "apiIntegrations.secret.apiKeyDescription" : "apiIntegrations.secret.webhookDescription")}
        </Alert>
        <div className="flex flex-col gap-3 sm:flex-row sm:items-center">
          <code
            dir="ltr"
            aria-label={t("apiIntegrations.secret.value")}
            className="min-w-0 flex-1 rounded-lg border border-line bg-surface-muted px-3 py-2 font-mono text-sm break-all text-ink select-all"
          >
            {secret?.value}
          </code>
          {secret ? <CopyButton value={secret.value} label={t("apiIntegrations.secret.copy")} className="self-start sm:self-center" /> : null}
        </div>
      </div>
    </Modal>
  );
}
