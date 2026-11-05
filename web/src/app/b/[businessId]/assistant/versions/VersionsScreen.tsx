"use client";

import Link from "next/link";

import { useBusiness, useBusinessFormat } from "@/components/business/BusinessContext";
import { IconChevronRight, IconSparkles } from "@/components/icons";
import { Button, Card, EmptyState, ErrorState, LoadingRegion } from "@/components/ui";
import { useI18n } from "@/i18n/client";
import { sortVersions } from "@/lib/assistant/versions";
import { formatScore } from "@/lib/assistant/autotests";
import { cn } from "@/lib/cn";
import { languageName } from "@/lib/format";
import { businessPath } from "@/lib/navigation";

import { useAssistant } from "../_components/AssistantContext";
import { VersionStatusBadge } from "../_components/VersionStatusBadge";
import { VersionsSkeleton } from "../_components/AssistantSkeletons";

/** Assistant -> Versions: every assembled version, newest first. */
export function VersionsScreen() {
  const { t, locale } = useI18n();
  const { business, isOwner } = useBusiness();
  const format = useBusinessFormat();
  const { versions, openBuild } = useAssistant();
  const base = `${businessPath(business.id, "assistant")}/versions`;
  const list = sortVersions(versions.data ?? []);

  if (versions.isLoading && !versions.data) {
    return (
      <LoadingRegion label={t("common.loading")}>
        <VersionsSkeleton />
      </LoadingRegion>
    );
  }
  if (versions.error && !versions.data) {
    return (
      <Card>
        <ErrorState error={versions.error} onRetry={versions.reload} />
      </Card>
    );
  }
  if (list.length === 0) {
    return (
      <Card>
        <EmptyState
          icon={<IconSparkles className="size-6" />}
          title={t("assistant.versions.emptyTitle")}
          description={isOwner ? t("assistant.versions.emptyDescription") : t("assistant.versions.emptyStaff")}
          action={
            isOwner ? (
              <Button leadingIcon={<IconSparkles className="size-4" aria-hidden />} onClick={openBuild}>
                {t("assistant.build.open")}
              </Button>
            ) : undefined
          }
        />
      </Card>
    );
  }

  return (
    <div className="space-y-4">
      {isOwner ? (
        // Advanced: an update by hand, checked and published from its page. The daily path is "Apply changes".
        <div className="flex justify-end">
          <Button variant="secondary" size="sm" leadingIcon={<IconSparkles className="size-4" aria-hidden />} onClick={openBuild}>
            {t("assistant.build.open")}
          </Button>
        </div>
      ) : null}
      <Card padded={false}>
        <ul className="divide-y divide-line">
          {list.map((version) => (
            <li key={version.id}>
              <Link
                href={`${base}/${encodeURIComponent(version.id)}`}
                className={cn(
                  "flex items-center gap-4 px-4 py-4 transition-colors hover:bg-surface-muted/60 sm:px-6",
                  "focus-visible:outline-2 focus-visible:outline-offset-[-2px] focus-visible:outline-focus",
                  version.status === "published" && "bg-success-soft/40",
                )}
              >
                <div className="min-w-0 flex-1 space-y-1">
                  <div className="flex flex-wrap items-center gap-2">
                    <span className="font-semibold text-ink">{t("assistant.versions.number", { number: version.version_number })}</span>
                    <VersionStatusBadge status={version.status} />
                    {version.test_score !== null && version.test_score !== undefined ? (
                      <span className="text-sm text-ink-muted">
                        {t("assistant.versions.score", { score: formatScore(version.test_score, locale) })}
                      </span>
                    ) : null}
                  </div>
                  <p className="text-sm text-ink-subtle">
                    {[
                      t("assistant.versions.built", { date: format.dateTime(version.created_at) }),
                      version.published_at ? t("assistant.versions.published", { date: format.dateTime(version.published_at) }) : null,
                    ]
                      .filter(Boolean)
                      .join(" · ")}
                  </p>
                  <p className="text-sm text-ink-subtle">
                    {version.languages.map((language) => languageName(language, locale)).join(", ")}
                    {version.is_voice_enabled ? ` · ${t("assistant.versions.voice")}` : ""}
                  </p>
                </div>
                <IconChevronRight className="size-5 shrink-0 text-ink-subtle rtl:-scale-x-100" aria-hidden />
              </Link>
            </li>
          ))}
        </ul>
      </Card>
    </div>
  );
}
