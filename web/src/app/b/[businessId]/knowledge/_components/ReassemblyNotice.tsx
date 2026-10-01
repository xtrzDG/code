"use client";

import { useBusiness } from "@/components/business/BusinessContext";
import { Alert, ButtonLink } from "@/components/ui";
import { useI18n } from "@/i18n/client";
import { businessPath } from "@/lib/navigation";

/**
 * The assistant answers from a frozen version: after changing what it knows,
 * the owner builds and publishes a new version.
 */
export function ReassemblyNotice({ className }: { className?: string }) {
  const { t } = useI18n();
  const { business, isOwner } = useBusiness();
  return (
    <Alert
      tone="info"
      className={className}
      title={t("knowledge.reassembly.title")}
      action={
        isOwner ? (
          <ButtonLink href={`${businessPath(business.id, "assistant")}/versions`} size="sm" variant="secondary">
            {t("knowledge.reassembly.action")}
          </ButtonLink>
        ) : undefined
      }
    >
      {isOwner ? t("knowledge.reassembly.owner") : t("knowledge.reassembly.staff")}
    </Alert>
  );
}
