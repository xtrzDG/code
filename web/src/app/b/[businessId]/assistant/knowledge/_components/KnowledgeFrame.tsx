"use client";

import type { ReactNode } from "react";

import { useBusiness } from "@/components/business/BusinessContext";
import { SectionTabs } from "@/components/content/SectionTabs";
import { PageHeader } from "@/components/ui";
import { useI18n } from "@/i18n/client";
import { businessPath } from "@/lib/navigation";

/** The Knowledge heading and its sub-pages (items, questions, import, resources). */
export function KnowledgeFrame({ children }: { children: ReactNode }) {
  const { t } = useI18n();
  const { business } = useBusiness();
  const base = businessPath(business.id, "assistant/knowledge");

  return (
    <>
      <PageHeader title={t("nav.knowledge")} description={t("pages.knowledge.description")} className="sm:mb-6" />
      <SectionTabs
        label={t("knowledge.tabs.label")}
        tabs={[
          { href: base, label: t("knowledge.tabs.items"), exact: true },
          { href: `${base}/questions`, label: t("knowledge.tabs.questions") },
          { href: `${base}/import`, label: t("knowledge.tabs.import") },
          { href: `${base}/resources`, label: t("knowledge.tabs.resources") },
        ]}
      />
      {children}
    </>
  );
}
