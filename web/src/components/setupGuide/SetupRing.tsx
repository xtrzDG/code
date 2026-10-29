"use client";

/**
 * The setup guide's progress in the bar (the sidebar on large screens, the
 * phone's top bar): a small ring that leads to the guide on the Overview,
 * shown to owners until the guide is finished.
 */

import Link from "next/link";

import { useBusiness } from "@/components/business/BusinessContext";
import { useI18n } from "@/i18n/client";
import { cn } from "@/lib/cn";
import { businessPath } from "@/lib/navigation";
import { showsRing } from "@/lib/setupGuide/guide";

import { ProgressRing } from "./ProgressRing";
import { useSetupProgress } from "./useSetupProgress";

export function SetupRing({ compact = false }: { compact?: boolean }) {
  const { t } = useI18n();
  const { business, isOwner } = useBusiness();
  const setup = useSetupProgress(business.id, { enabled: isOwner });
  if (!setup.data || !showsRing(setup.data, isOwner)) {
    return null;
  }
  const percent = setup.data.guide.percent;
  const label = t("setupGuide.ring.label", { percent });
  return (
    <Link
      href={`${businessPath(business.id, "overview")}#setup-guide`}
      aria-label={label}
      title={label}
      className={cn(
        "flex min-h-11 items-center gap-2 rounded-xl text-sm text-ink-muted transition-colors hover:bg-surface-muted hover:text-ink focus-visible:outline-2 focus-visible:outline-focus",
        compact ? "justify-center px-1" : "px-2 py-1.5",
      )}
    >
      <ProgressRing percent={percent} size={compact ? 28 : 32} label={label} showNumber={compact} />
      {compact ? null : (
        <span className="min-w-0 truncate">
          <span className="font-medium text-ink">{t("setupGuide.ring.title")}</span>{" "}
          <span className="tabular-nums">{t("setupGuide.ring.short", { percent })}</span>
        </span>
      )}
    </Link>
  );
}
