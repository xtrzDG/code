"use client";

/**
 * What platform support sees over a client's cabinet: read only (or until
 * when the owner allowed changes), when the look ends, "Leave the cabinet".
 */

import { useRouter } from "next/navigation";

import type { SupportAccessView } from "@/api/types";
import { Button, useToast } from "@/components/ui";
import { useI18n } from "@/i18n/client";
import { formatTime } from "@/lib/format";
import { adminClientPath } from "@/lib/navigation";
import { supportUntil } from "@/lib/supportAccess";

import type { useSupportAccess } from "./useSupportAccess";

export function SupportViewerPanel({
  view,
  businessId,
  businessName,
  actions,
}: {
  view: SupportAccessView;
  businessId: string;
  businessName: string;
  actions: ReturnType<typeof useSupportAccess>;
}) {
  const { t, locale } = useI18n();
  const toast = useToast();
  const router = useRouter();
  const until = supportUntil(view);
  const time = (value: number) => formatTime(value, { locale });
  const writeUntil = view.write_access?.expires_at;

  const leave = async () => {
    if (await actions.leave()) {
      toast.success(t("supportAccess.support.left"));
      router.push(adminClientPath(businessId));
    }
  };

  return (
    <div className="flex flex-wrap items-center gap-x-4 gap-y-2">
      <div className="min-w-0 flex-1 space-y-1">
        <p className="font-medium text-ink">{t("supportAccess.support.title", { name: businessName })}</p>
        <p className="text-ink-muted">
          {[
            view.viewer_can_write && writeUntil
              ? t("supportAccess.support.canWrite", { time: time(writeUntil) })
              : t("supportAccess.support.readOnly"),
            until ? t("supportAccess.support.until", { time: time(until) }) : null,
          ]
            .filter(Boolean)
            .join(" · ")}
        </p>
      </div>
      <Button variant="secondary" size="sm" isLoading={actions.leaving.isPending} onClick={() => void leave()}>
        {t("supportAccess.support.leave")}
      </Button>
    </div>
  );
}
