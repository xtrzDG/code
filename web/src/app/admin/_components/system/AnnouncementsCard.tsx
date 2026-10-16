"use client";

import Link from "next/link";
import { useState } from "react";

import { IconExternal, IconMegaphone, IconPlus } from "@/components/icons";
import { LoadMore } from "@/components/insights/common";
import { Badge, Button, Card, ConfirmDialog, EmptyState, ErrorState, SkeletonText } from "@/components/ui";
import { useToast } from "@/components/ui/Toast";
import { useI18n } from "@/i18n/client";
import { listFormat } from "@/lib/intl/formatters";
import { ANNOUNCEMENT_TONES } from "@/lib/help/platformStatus";
import { STATUS_PATH } from "@/lib/help/helpTopics";

import type { AdminAnnouncement, CreateAnnouncementBody, UpdateAnnouncementBody } from "../../_lib/announcementForm";
import { useAnnouncements } from "../../_lib/useAnnouncements";
import { AnnouncementDialog } from "./AnnouncementDialog";
import { useSystemFormat } from "./useSystemFormat";

/**
 * What the public status page and the banner over every cabinet say: the
 * team's announcements, newest first, with "New announcement", "Update"
 * and "Resolve".
 */
export function AnnouncementsCard() {
  const { t } = useI18n();
  const toast = useToast();
  const { announcements, publish, update, creation, change } = useAnnouncements();
  const [editing, setEditing] = useState<AdminAnnouncement | "new" | null>(null);
  const [resolving, setResolving] = useState<AdminAnnouncement | null>(null);
  const title = t("adminStatus.title");
  const items = announcements.items;

  const onPublish = async (body: CreateAnnouncementBody) => {
    const published = await publish(body);
    if (published) {
      toast.success(t("adminStatus.published"));
    }
    return published;
  };
  const onUpdate = async (id: string, body: UpdateAnnouncementBody) => {
    const saved = await update(id, body);
    if (saved) {
      toast.success(t("adminStatus.saved"));
    }
    return saved;
  };
  const resolve = async () => {
    if (resolving && (await update(resolving.id, { resolve: true }))) {
      toast.success(t("adminStatus.resolvedToast"));
      setResolving(null);
    }
  };

  return (
    <Card
      aria-label={title}
      title={title}
      description={t("adminStatus.description")}
      actions={
        <>
          <Link href={STATUS_PATH} target="_blank" className="inline-flex items-center gap-1.5 text-sm font-medium text-accent hover:underline">
            {t("adminStatus.openPage")}
            <IconExternal className="size-3.5" aria-hidden />
          </Link>
          <Button variant="secondary" leadingIcon={<IconPlus className="size-4" aria-hidden />} onClick={() => setEditing("new")}>
            {t("adminStatus.create")}
          </Button>
        </>
      }
    >
      {announcements.error && !items ? (
        <ErrorState error={announcements.error} onRetry={announcements.reload} />
      ) : !items ? (
        <SkeletonText lines={3} />
      ) : items.length === 0 ? (
        <EmptyState icon={<IconMegaphone className="size-6" />} title={t("adminStatus.none")} description={t("adminStatus.noneDescription")} />
      ) : (
        <>
          <ul className="divide-y divide-line">
            {items.map((announcement) => (
              <AnnouncementRow
                key={announcement.id}
                announcement={announcement}
                onEdit={() => setEditing(announcement)}
                onResolve={() => setResolving(announcement)}
              />
            ))}
          </ul>
          <LoadMore hasMore={announcements.hasMore} isLoading={announcements.isLoadingMore} error={announcements.moreError} onMore={announcements.loadMore} />
        </>
      )}

      <AnnouncementDialog
        editing={editing}
        onClose={() => setEditing(null)}
        onPublish={onPublish}
        onUpdate={onUpdate}
        isSaving={creation.isPending || change.isPending}
        error={editing === "new" ? creation.error : change.error}
      />
      <ConfirmDialog
        open={resolving !== null}
        onClose={() => setResolving(null)}
        onConfirm={resolve}
        title={t("adminStatus.resolveTitle")}
        description={t("adminStatus.resolveBody")}
        confirmLabel={t("adminStatus.resolve")}
        tone="primary"
        isPending={change.isPending}
        error={change.error}
      />
    </Card>
  );
}

function AnnouncementRow({ announcement, onEdit, onResolve }: { announcement: AdminAnnouncement; onEdit: () => void; onResolve: () => void }) {
  const { t, locale } = useI18n();
  const format = useSystemFormat();
  const english = announcement.messages.find((message) => message.language === "en") ?? announcement.messages[0];
  const isActive = announcement.status === "active";
  const components = listFormat(locale, { type: "conjunction" }).format(
    announcement.components.map((component) => t(`platformStatus.components.${component}`)),
  );
  return (
    <li className="space-y-2 py-4 first:pt-0 last:pb-0" data-announcement-row={announcement.id}>
      <div className="flex flex-wrap items-center gap-2">
        <Badge tone={ANNOUNCEMENT_TONES[announcement.level]}>{t(`platformStatus.announcementLevels.${announcement.level}`)}</Badge>
        <Badge tone={isActive ? "warning" : "success"}>{t(`adminStatus.status.${announcement.status}`)}</Badge>
        {isActive ? (
          <span className="ms-auto flex gap-2">
            <Button size="sm" variant="secondary" onClick={onEdit}>
              {t("adminStatus.edit")}
            </Button>
            <Button size="sm" variant="secondary" onClick={onResolve}>
              {t("adminStatus.resolve")}
            </Button>
          </span>
        ) : null}
      </div>
      {english ? (
        <p className="break-words text-ink" lang={english.language} dir="auto">
          {english.text}
        </p>
      ) : null}
      <p className="flex flex-wrap gap-x-4 gap-y-1 text-sm text-ink-muted">
        {announcement.components.length > 0 ? <span>{t("platformStatus.affects", { components })}</span> : null}
        <span>{t("platformStatus.since", { time: format.when(announcement.starts_at) })}</span>
        {announcement.expected_end_at ? <span>{t("platformStatus.expectedEnd", { time: format.when(announcement.expected_end_at) })}</span> : null}
        {announcement.resolved_at ? <span>{t("platformStatus.resolved", { time: format.when(announcement.resolved_at) })}</span> : null}
      </p>
    </li>
  );
}
