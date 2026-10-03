"use client";

import type { ReactNode } from "react";

import { useBusiness, useBusinessFormat } from "@/components/business/BusinessContext";
import { IconChat, IconFlask, IconRocket, IconUndo } from "@/components/icons";
import { Alert, Button, ButtonLink, Card } from "@/components/ui";
import { useI18n } from "@/i18n/client";
import { formatScore } from "@/lib/assistant/autotests";
import type { AssistantVersionDetails, VersionActions } from "@/lib/assistant/versions";
import { languageName } from "@/lib/format";
import { businessPath } from "@/lib/navigation";

import { VersionStatusBadge } from "../../../_components/VersionStatusBadge";

export type VersionDialog = "publish" | "forcePublish" | "rollback" | "autotests";

/** The version's number, status, dates, languages and score, and what can be done with it now. */
export function VersionHeaderCard({
  details,
  actions,
  canRunAutotests,
  isRunning,
  onOpen,
}: {
  details: AssistantVersionDetails;
  actions: VersionActions;
  canRunAutotests: boolean;
  isRunning: boolean;
  onOpen: (dialog: VersionDialog) => void;
}) {
  const { t, locale } = useI18n();
  const { business, isOwner, isPlatformAdmin } = useBusiness();
  const format = useBusinessFormat();
  const base = businessPath(business.id, "assistant");
  return (
    <Card>
      <div className="flex flex-col gap-5 lg:flex-row lg:items-start lg:justify-between">
        <div className="min-w-0 space-y-3">
          <div className="flex flex-wrap items-center gap-3">
            <h2 className="text-xl font-semibold text-ink">{t("assistant.versions.number", { number: details.version_number })}</h2>
            <VersionStatusBadge status={details.status} />
          </div>
          <dl className="grid gap-x-8 gap-y-2 text-sm sm:grid-cols-2">
            <Meta label={t("assistant.detail.built")}>{format.dateTime(details.created_at)}</Meta>
            {details.published_at ? <Meta label={t("assistant.detail.publishedAt")}>{format.dateTime(details.published_at)}</Meta> : null}
            <Meta label={t("assistant.detail.languages")}>
              {details.languages
                .map((language) =>
                  language === details.default_language
                    ? t("assistant.detail.mainLanguage", { language: languageName(language, locale) })
                    : languageName(language, locale),
                )
                .join(", ")}
            </Meta>
            <Meta label={t("assistant.detail.testScore")}>
              {details.test_score !== null && details.test_score !== undefined
                ? t("assistant.autotests.scoreValue", { score: formatScore(details.test_score, locale) })
                : t("assistant.detail.noScore")}
            </Meta>
          </dl>
        </div>
        <div className="flex flex-wrap gap-2 lg:justify-end">
          <ButtonLink
            href={`${base}?version=${encodeURIComponent(details.id)}`}
            variant="secondary"
            leadingIcon={<IconChat className="size-4" aria-hidden />}
            // One line: "Проверить в чате" must not break between its words.
            className="whitespace-nowrap"
          >
            {t("assistant.detail.testInChat")}
          </ButtonLink>
          {canRunAutotests ? (
            <Button
              variant={actions.publish ? "secondary" : "primary"}
              leadingIcon={<IconFlask className="size-4" aria-hidden />}
              onClick={() => onOpen("autotests")}
            >
              {t("assistant.autotests.run")}
            </Button>
          ) : null}
          {actions.publish ? (
            <Button leadingIcon={<IconRocket className="size-4" aria-hidden />} onClick={() => onOpen("publish")}>
              {t("assistant.publish.open")}
            </Button>
          ) : null}
          {actions.forcePublish && !isRunning ? (
            <Button variant="danger" leadingIcon={<IconRocket className="size-4" aria-hidden />} onClick={() => onOpen("forcePublish")}>
              {t("assistant.publish.forceOpen")}
            </Button>
          ) : null}
          {actions.rollback ? (
            <Button variant="danger" leadingIcon={<IconUndo className="size-4" aria-hidden />} onClick={() => onOpen("rollback")}>
              {t("assistant.rollback.open")}
            </Button>
          ) : null}
        </div>
      </div>
      {details.status === "published" ? (
        <Alert tone="success" className="mt-5" title={t("assistant.detail.liveTitle")}>
          {t("assistant.detail.liveDescription")}
        </Alert>
      ) : null}
      {details.status === "archived" ? (
        <Alert tone="info" className="mt-5">
          {t("assistant.detail.archivedDescription")}
        </Alert>
      ) : null}
      {!isOwner && !isPlatformAdmin ? (
        <p className="mt-5 text-sm text-ink-muted">{t("assistant.detail.ownerOnly")}</p>
      ) : null}
    </Card>
  );
}

function Meta({ label, children }: { label: string; children: ReactNode }) {
  return (
    <div className="flex flex-wrap gap-x-2">
      <dt className="text-ink-subtle">{label}:</dt>
      <dd className="text-ink">{children}</dd>
    </div>
  );
}
