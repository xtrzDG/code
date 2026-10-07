"use client";

/**
 * Over every page of a business's cabinet while platform support looks
 * into it (or may make changes): the owner sees who, why and until when,
 * ends it or lets support make changes; staff see who; support itself sees
 * that it may only look, and leaves. Hidden otherwise.
 */

import { IconShield } from "@/components/icons";
import { useI18n } from "@/i18n/client";
import { cn } from "@/lib/cn";
import { isSupportPresent } from "@/lib/supportAccess";

import { useBusiness } from "../business/BusinessContext";
import { OwnerSupportPanel } from "./support/OwnerSupportPanel";
import { SupportViewerPanel } from "./support/SupportViewerPanel";
import { useSupportAccess } from "./support/useSupportAccess";

export function SupportBanner() {
  const { t } = useI18n();
  const { business, isOwner } = useBusiness();
  const actions = useSupportAccess(business.id);
  const view = actions.access.data;

  if (!view || !(view.is_support_viewer || isSupportPresent(view))) {
    return null;
  }
  return (
    <section
      aria-label={t("supportAccess.label")}
      data-testid="support-banner"
      className={cn(
        "mb-5 flex gap-3 rounded-2xl border px-4 py-3 text-sm",
        view.is_support_viewer ? "border-info/30 bg-info-soft/60" : "border-warning/40 bg-warning-soft/60",
      )}
    >
      <IconShield className={cn("mt-0.5 size-5 shrink-0", view.is_support_viewer ? "text-info" : "text-warning")} aria-hidden />
      <div className="min-w-0 flex-1">
        {view.is_support_viewer ? (
          <SupportViewerPanel view={view} businessId={business.id} businessName={business.name} actions={actions} />
        ) : (
          <OwnerSupportPanel view={view} isOwner={isOwner} actions={actions} timeZone={business.timezone} />
        )}
      </div>
    </section>
  );
}
