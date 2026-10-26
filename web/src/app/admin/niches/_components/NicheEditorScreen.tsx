"use client";

/**
 * /admin/niches/[nicheKey]?language=: one niche template's owner-facing
 * texts in one of the cabinet's languages beside the code's wording, a
 * preview of the profile questions as an owner sees them, the draft's
 * actions and the published versions.
 */

import { useRouter } from "next/navigation";

import { Tabs } from "@/components/content/Tabs";
import { IconArrowLeft } from "@/components/icons";
import { ButtonLink, Card, ErrorState, LoadingRegion, PageHeader, SkeletonCard } from "@/components/ui";
import { useI18n } from "@/i18n/client";
import { LOCALE_NATIVE_NAMES, isLocale } from "@/i18n/config";
import { ADMIN_NICHES_PATH, adminNichePath } from "@/lib/navigation";

import { startingValues } from "../_lib/nicheTexts";
import { useNicheEditor, useNicheOverview } from "../_lib/useNicheTexts";
import { NicheTextsForm } from "./NicheTextsForm";
import { NicheVersionsCard } from "./NicheVersionsCard";

export function NicheEditorScreen({ nicheKey, language }: { nicheKey: string; language: string }) {
  const { t, locale } = useI18n();
  const router = useRouter();
  const niche = useNicheEditor(nicheKey, language);
  // The niche is named in the admin's own language, whichever language its texts are edited in.
  const overview = useNicheOverview(locale);
  const editor = niche.editor.data;
  const status = editor?.status;
  const name = overview.data?.items?.find((item) => item.niche_key === nicheKey)?.name ?? status?.name;
  const languages = editor?.languages ?? [language];

  return (
    <>
      <ButtonLink
        href={ADMIN_NICHES_PATH}
        variant="ghost"
        size="sm"
        className="mb-4 -ms-3"
        leadingIcon={<IconArrowLeft className="size-4 rtl:-scale-x-100" aria-hidden />}
      >
        {t("adminNiches.editor.back")}
      </ButtonLink>
      <PageHeader
        title={name ?? t("adminNiches.title")}
        description={
          status
            ? [
                status.published_version > 0
                  ? t("adminNiches.editor.inForce", { version: status.published_version })
                  : t("adminNiches.editor.onCode"),
                status.has_draft ? t("adminNiches.editor.draftWaiting") : null,
              ]
                .filter(Boolean)
                .join(" · ")
            : undefined
        }
      />
      {niche.editor.error && !editor ? (
        <Card>
          <ErrorState error={niche.editor.error} onRetry={niche.editor.reload} />
        </Card>
      ) : (
        <div className="space-y-6">
          <Tabs
            label={t("adminNiches.editor.languages")}
            tabs={languages.map((tag) => ({ key: tag, label: isLocale(tag) ? LOCALE_NATIVE_NAMES[tag] : tag }))}
            selected={language}
            onSelect={(tag) => router.replace(adminNichePath(nicheKey, tag), { scroll: false })}
          >
            {editor && editor.language === language ? (
              <NicheTextsForm
                key={`${editor.language}:${JSON.stringify(startingValues(editor))}`}
                editor={editor}
                niche={niche}
                nicheName={name ?? nicheKey}
              />
            ) : (
              <NicheEditorSkeleton />
            )}
          </Tabs>
          <NicheVersionsCard niche={niche} nicheName={name ?? nicheKey} />
        </div>
      )}
    </>
  );
}

/** The editor while it loads (also the route's loading.tsx). */
export function NicheEditorSkeleton() {
  const { t } = useI18n();
  return (
    <LoadingRegion label={t("adminNiches.loading")}>
      <SkeletonCard lines={6} />
    </LoadingRegion>
  );
}
