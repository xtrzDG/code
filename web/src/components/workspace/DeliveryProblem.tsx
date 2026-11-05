"use client";

import { useOptionalBusiness } from "@/components/business/BusinessContext";
import { useI18n } from "@/i18n/client";
import { cn } from "@/lib/cn";

/**
 * Why something did not get through: owners and staff read a plain
 * message (`message`, or the common one); the server's raw error, which
 * can name a provider or a setting, is shown to platform admins only.
 */
export function DeliveryProblem({
  error,
  message,
  className,
}: {
  error: string | null | undefined;
  message?: string;
  className?: string;
}) {
  const { t } = useI18n();
  const detail = useAdminErrorDetail()(error);
  return (
    <div className={cn("text-sm text-danger", className)}>
      <p>{message ?? t("common.deliveryProblem")}</p>
      {detail ? (
        <p dir="auto" className="mt-0.5 font-mono text-xs break-words">
          {detail}
        </p>
      ) : null}
    </div>
  );
}

/** The server's raw error for platform admins, null for everyone else (e.g. a toast's description). */
export function useAdminErrorDetail(): (error: string | null | undefined) => string | null {
  const isPlatformAdmin = useOptionalBusiness()?.isPlatformAdmin ?? false;
  return (error) => (isPlatformAdmin && error ? error : null);
}
