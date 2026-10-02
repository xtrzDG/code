"use client";

import { useState } from "react";

import { api } from "@/api/client";
import { useApiMutation } from "@/api/hooks";
import { useBusiness } from "@/components/business/BusinessContext";
import { ConfirmDialog } from "@/components/content/ConfirmDialog";
import { Alert, Checkbox, useToast } from "@/components/ui";
import { useI18n } from "@/i18n/client";
import type { AssistantVersionDetails } from "@/lib/assistant/versions";

import { refusalOf, type RefusalState } from "../_lib/refusal";
import { RefusalReasons } from "./RefusalReasons";

/**
 * Publish a version (owner): a confirmation, and the API's refusal reasons
 * (by their codes: trial, agreement, profile, staff contact, autotests,
 * voice setup) with links to fix them.
 * `force` publishes a version that did not pass its autotests (platform admins).
 */
export function PublishDialog({
  version,
  liveNumber,
  force,
  onClose,
  onPublished,
  onRunAutotests,
  onRefused,
}: {
  version: AssistantVersionDetails;
  liveNumber: number | null;
  force: boolean;
  onClose: () => void;
  onPublished: (version: AssistantVersionDetails) => void;
  onRunAutotests: () => void;
  /** The API refused: what the page shows may be out of date. */
  onRefused: () => void;
}) {
  const { t } = useI18n();
  const toast = useToast();
  const { business } = useBusiness();
  const [refusal, setRefusal] = useState<RefusalState | null>(null);
  const [acknowledged, setAcknowledged] = useState(false);

  const publish = useApiMutation(
    (acceptFailedTests: boolean) =>
      api.POST("/v1/businesses/{business_id}/assistant-versions/{version_id}/publish", {
        params: { path: { business_id: business.id, version_id: version.id } },
        body: { accept_failed_tests: acceptFailedTests },
      }),
    { errorToast: false },
  );

  const submit = async () => {
    setRefusal(null);
    const result = await publish.run(force);
    if (result.ok) {
      toast.success(t("assistant.publish.done", { number: result.data.version_number }));
      onPublished(result.data);
      return;
    }
    const refused = refusalOf(result.error);
    if (refused) {
      setRefusal(refused);
      onRefused();
    } else {
      toast.error(result.error);
    }
  };

  return (
    <ConfirmDialog
      open
      variant={force ? "danger" : "primary"}
      title={force ? t("assistant.publish.forceTitle", { number: version.version_number }) : t("assistant.publish.title", { number: version.version_number })}
      description={
        liveNumber !== null
          ? t("assistant.publish.descriptionReplace", { live: liveNumber })
          : t("assistant.publish.descriptionFirst")
      }
      confirmLabel={force ? t("assistant.publish.forceConfirm") : t("assistant.publish.confirm")}
      pendingLabel={t("assistant.publish.publishing")}
      isPending={publish.isPending}
      confirmDisabled={force && !acknowledged}
      onConfirm={() => void submit()}
      onClose={onClose}
    >
      {force ? (
        <>
          <Alert tone="danger" title={t("assistant.publish.forceWarningTitle")}>
            {t("assistant.publish.forceWarning")}
          </Alert>
          <Checkbox
            id="publish-acknowledge"
            label={t("assistant.publish.forceAcknowledge")}
            checked={acknowledged}
            onChange={(event) => setAcknowledged(event.target.checked)}
          />
        </>
      ) : null}
      {refusal ? (
        <div role="alert" className="space-y-3 rounded-xl border border-danger/25 bg-danger-soft px-4 py-3">
          <p className="text-sm font-medium text-danger">{t("assistant.publish.refused")}</p>
          <RefusalReasons
            reasons={refusal.reasons}
            error={refusal.error}
            onRunAutotests={() => {
              onClose();
              onRunAutotests();
            }}
          />
        </div>
      ) : null}
    </ConfirmDialog>
  );
}
