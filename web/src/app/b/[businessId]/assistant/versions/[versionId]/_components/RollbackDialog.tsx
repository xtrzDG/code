"use client";

import { useState } from "react";

import { api } from "@/api/client";
import { useApiMutation } from "@/api/hooks";
import { useBusiness } from "@/components/business/BusinessContext";
import { ConfirmDialog } from "@/components/content/ConfirmDialog";
import { useToast } from "@/components/ui";
import { useI18n } from "@/i18n/client";
import type { AssistantVersionDetails } from "@/lib/assistant/versions";

import { refusalOf, type RefusalState } from "../_lib/refusal";
import { RefusalReasons } from "./RefusalReasons";

/** Make an earlier (archived) version live again. */
export function RollbackDialog({
  version,
  liveNumber,
  onClose,
  onRolledBack,
  onRefused,
}: {
  version: AssistantVersionDetails;
  liveNumber: number | null;
  onClose: () => void;
  onRolledBack: (version: AssistantVersionDetails) => void;
  onRefused: () => void;
}) {
  const { t } = useI18n();
  const toast = useToast();
  const { business } = useBusiness();
  const [refusal, setRefusal] = useState<RefusalState | null>(null);

  const rollback = useApiMutation(
    () =>
      api.POST("/v1/businesses/{business_id}/assistant-versions/{version_id}/rollback", {
        params: { path: { business_id: business.id, version_id: version.id } },
      }),
    { errorToast: false },
  );

  const submit = async () => {
    setRefusal(null);
    const result = await rollback.run();
    if (result.ok) {
      toast.success(t("assistant.rollback.done", { number: result.data.version_number }));
      onRolledBack(result.data);
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
      variant="danger"
      title={t("assistant.rollback.title", { number: version.version_number })}
      description={
        liveNumber !== null
          ? t("assistant.rollback.descriptionReplace", { live: liveNumber, number: version.version_number })
          : t("assistant.rollback.description", { number: version.version_number })
      }
      confirmLabel={t("assistant.rollback.confirm")}
      pendingLabel={t("assistant.rollback.rollingBack")}
      isPending={rollback.isPending}
      onConfirm={() => void submit()}
      onClose={onClose}
    >
      {refusal ? (
        <div role="alert" className="space-y-3 rounded-xl border border-danger/25 bg-danger-soft px-4 py-3">
          <p className="text-sm font-medium text-danger">{t("assistant.rollback.refused")}</p>
          <RefusalReasons reasons={refusal.reasons} error={refusal.error} />
        </div>
      ) : null}
    </ConfirmDialog>
  );
}
