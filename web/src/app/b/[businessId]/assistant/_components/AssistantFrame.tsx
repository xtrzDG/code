"use client";

import { useMemo, useState, type ReactNode } from "react";

import { sectionQueries } from "@/api/sectionQueries";
import { useQuery } from "@/api/useQuery";
import { useApplyChanges } from "@/components/assistant/ApplyChangesContext";
import { useBusiness, useBusinessFormat } from "@/components/business/BusinessContext";
import { IconSparkles } from "@/components/icons";
import { SectionFrame } from "@/components/shell/SectionFrame";
import { Button } from "@/components/ui";
import { useI18n } from "@/i18n/client";
import { liveVersion, sortVersions } from "@/lib/assistant/versions";

import { AssistantContext, type AssistantContextValue } from "./AssistantContext";
import { BuildVersionDialog } from "./BuildVersionDialog";

/**
 * The Assistant section: try it, what it knows, hours and rules, where it
 * answers and (under Advanced) versions and checks. Above the tabs whether
 * customers get answers, and for owners "Apply changes": the sheet with
 * the changes customers do not get yet (components/assistant). Building a
 * version by hand stays under Advanced (the versions page).
 */
export function AssistantFrame({ children }: { children: ReactNode }) {
  const { t } = useI18n();
  const { business, isOwner } = useBusiness();
  const format = useBusinessFormat();
  const applyChanges = useApplyChanges();
  const [isBuilding, setBuilding] = useState(false);

  const versionsQuery = sectionQueries.assistantVersions(business.id);
  const versions = useQuery(versionsQuery.key, versionsQuery.fetch);
  const value = useMemo<AssistantContextValue>(() => ({ versions, openBuild: () => setBuilding(true) }), [versions]);

  const live = liveVersion(sortVersions(versions.data ?? []));

  return (
    <AssistantContext.Provider value={value}>
      <SectionFrame
        section="assistant"
        actions={
          isOwner ? (
            <Button
              leadingIcon={<IconSparkles className="size-4" aria-hidden />}
              onClick={applyChanges.open}
              title={t("applyChanges.hint")}
              aria-haspopup="dialog"
            >
              {t("applyChanges.sheet.apply")}
            </Button>
          ) : undefined
        }
        aside={
          versions.data ? (
            <p className="-mt-2 mb-5 flex items-start gap-2 text-sm text-ink-muted" aria-live="polite">
              <span
                aria-hidden
                className={live ? "mt-1.5 size-2.5 shrink-0 animate-pulse rounded-full bg-success" : "mt-1.5 size-2.5 shrink-0 rounded-full bg-warning"}
              />
              <span>
                {live
                  ? live.published_at
                    ? t("applyChanges.status.liveSince", { date: format.dateTime(live.published_at) })
                    : t("applyChanges.status.live")
                  : t("applyChanges.status.notLive")}
              </span>
            </p>
          ) : null
        }
      >
        {children}
      </SectionFrame>
      {isBuilding ? (
        <BuildVersionDialog
          onClose={() => setBuilding(false)}
          // The new version reaches the list through the build's invalidation.
          onBuilt={() => setBuilding(false)}
        />
      ) : null}
    </AssistantContext.Provider>
  );
}
