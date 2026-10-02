"use client";

import { useMemo, useState, type ReactNode } from "react";

import { sectionQueries } from "@/api/sectionQueries";
import { useQuery } from "@/api/useQuery";
import { useBusiness, useBusinessFormat } from "@/components/business/BusinessContext";
import { SectionTabs } from "@/components/content/SectionTabs";
import { IconSparkles } from "@/components/icons";
import { Button, PageHeader } from "@/components/ui";
import { useI18n } from "@/i18n/client";
import { liveVersion, sortVersions } from "@/lib/assistant/versions";
import { businessPath } from "@/lib/navigation";

import { AssistantContext, type AssistantContextValue } from "./AssistantContext";
import { BuildVersionDialog } from "./BuildVersionDialog";

/** The Assistant heading, the live version, "Build a new version" and the tabs. */
export function AssistantFrame({ children }: { children: ReactNode }) {
  const { t } = useI18n();
  const { business, isOwner } = useBusiness();
  const format = useBusinessFormat();
  const base = businessPath(business.id, "assistant");
  const [isBuilding, setBuilding] = useState(false);

  const versionsQuery = sectionQueries.assistantVersions(business.id);
  const versions = useQuery(versionsQuery.key, versionsQuery.fetch);
  const value = useMemo<AssistantContextValue>(() => ({ versions, openBuild: () => setBuilding(true) }), [versions]);

  const live = liveVersion(sortVersions(versions.data ?? []));

  return (
    <AssistantContext.Provider value={value}>
      <PageHeader
        title={t("nav.assistant")}
        description={t("pages.assistant.description")}
        className="sm:mb-6"
        actions={
          isOwner ? (
            <Button leadingIcon={<IconSparkles className="size-4" aria-hidden />} onClick={() => setBuilding(true)}>
              {t("assistant.build.open")}
            </Button>
          ) : undefined
        }
      />
      {versions.data ? (
        <p className="-mt-2 mb-5 flex items-start gap-2 text-sm text-ink-muted" aria-live="polite">
          <span
            aria-hidden
            className={live ? "mt-1.5 size-2.5 shrink-0 rounded-full bg-success" : "mt-1.5 size-2.5 shrink-0 rounded-full bg-warning"}
          />
          <span>
            {live
            ? live.published_at
              ? t("assistant.liveSince", { number: live.version_number, date: format.dateTime(live.published_at) })
              : t("assistant.live", { number: live.version_number })
            : t("assistant.notLive")}
          </span>
        </p>
      ) : null}
      <SectionTabs
        label={t("assistant.tabs.label")}
        tabs={[
          { href: base, label: t("assistant.tabs.chat"), exact: true },
          { href: `${base}/versions`, label: t("assistant.tabs.versions") },
        ]}
      />
      {children}
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
