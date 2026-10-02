"use client";

import { useMemo, useState, type ReactNode } from "react";

import { sectionQueries } from "@/api/sectionQueries";
import { useQuery } from "@/api/useQuery";
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
 * answers and (under Advanced) versions and autotests. Above the tabs the
 * version customers talk to now, and for owners "Apply changes": a new
 * version built from the profile and knowledge.
 */
export function AssistantFrame({ children }: { children: ReactNode }) {
  const { t } = useI18n();
  const { business, isOwner } = useBusiness();
  const format = useBusinessFormat();
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
              onClick={() => setBuilding(true)}
              title={t("navigation.applyChangesHint")}
            >
              {t("navigation.applyChanges")}
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
                    ? t("assistant.liveSince", { number: live.version_number, date: format.dateTime(live.published_at) })
                    : t("assistant.live", { number: live.version_number })
                  : t("assistant.notLive")}
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
