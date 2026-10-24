"use client";

/**
 * The top of a section's editor: the way back to all sections, whether
 * the changes are saved ("Saving…", "Saved", or what went wrong), and the
 * other sections to jump to.
 */

import Link from "next/link";

import { IconAlert, IconArrowLeft, IconCheck } from "@/components/icons";
import { SectionTabs } from "@/components/content/SectionTabs";
import type { SaveState } from "@/components/setup/TunnelHeader";
import { Spinner } from "@/components/ui";
import { useI18n } from "@/i18n/client";
import { cn } from "@/lib/cn";
import { PROFILE_SECTIONS, profilePath, profileSectionPath } from "@/lib/profile/sections";

function SaveStatus({ state }: { state: SaveState }) {
  const { t } = useI18n();
  return (
    <p
      role="status"
      data-save-state={state}
      className={cn(
        "inline-flex min-h-8 items-center gap-1.5 rounded-full px-3 text-xs font-medium",
        state === "failed" ? "bg-warning-soft text-warning" : "bg-surface-muted/80 text-ink-muted",
      )}
    >
      {state === "saving" ? <Spinner size="sm" /> : state === "saved" ? <IconCheck className="size-3.5 text-success" aria-hidden /> : state === "failed" ? <IconAlert className="size-3.5" aria-hidden /> : null}
      {t(`profileEdit.status.${state}`)}
    </p>
  );
}

export function EditorBar({ businessId, state }: { businessId: string; state: SaveState }) {
  const { t } = useI18n();
  return (
    <div className="space-y-4">
      <div className="flex flex-wrap items-center justify-between gap-3">
        <Link
          href={profilePath(businessId)}
          className="inline-flex min-h-9 items-center gap-1.5 rounded-lg pe-2 text-sm font-medium text-ink-muted transition-colors hover:text-ink focus-visible:outline-2 focus-visible:outline-focus"
        >
          <IconArrowLeft className="size-4 rtl:-scale-x-100" aria-hidden />
          {t("profileEdit.back")}
        </Link>
        <SaveStatus state={state} />
      </div>
      <SectionTabs
        label={t("profileEdit.sectionsLabel")}
        tabs={PROFILE_SECTIONS.map((section) => ({ href: profileSectionPath(businessId, section), label: t(`profileEdit.sections.${section}.title`) }))}
        className="mb-0"
      />
    </div>
  );
}
