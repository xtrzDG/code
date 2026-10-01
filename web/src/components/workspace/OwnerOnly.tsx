"use client";

import { IconShield } from "@/components/icons";
import { Alert, EmptyState } from "@/components/ui";
import { useI18n } from "@/i18n/client";

/** A note above controls a staff member can see but not change. */
export function OwnerOnlyNote({ className }: { className?: string }) {
  const { t } = useI18n();
  return (
    <Alert tone="info" className={className}>
      {t("workspace.ownerOnlyChange")}
    </Alert>
  );
}

/** Instead of data only the owner may see (the API answered 403). */
export function OwnerOnlyState({ className }: { className?: string }) {
  const { t } = useI18n();
  return (
    <EmptyState
      className={className}
      icon={<IconShield className="size-6" />}
      title={t("workspace.ownerOnlyTitle")}
      description={t("workspace.ownerOnlyDescription")}
    />
  );
}
