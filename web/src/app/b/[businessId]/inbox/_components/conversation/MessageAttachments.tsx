"use client";

/**
 * What a customer sent besides text, in the transcript: a voice message to
 * play with what the assistant heard, a photo, a place with a map link, and
 * what the assistant could not read (a sticker, a contact card, a file) with
 * why; the customer was asked to write instead. Files the retention purge
 * removed say so.
 */

import type { ReactNode } from "react";

import { IconAlert, IconExternal } from "@/components/icons";
import { useI18n } from "@/i18n/client";
import { cn } from "@/lib/cn";

import {
  ATTACHMENT_KIND_LABELS,
  ATTACHMENT_PROBLEMS,
  formatCoordinates,
  hasStoredFile,
  placeSubtitle,
  placeTitle,
  safeMapUrl,
  voiceDuration,
  voiceTranscript,
  type AttachmentKind,
  type MessageAttachmentView,
  type SharedLocation,
} from "../../_lib/messageMedia";
import { ATTACHMENT_ICONS } from "../attachmentIcons";
import { PhotoAttachment } from "./PhotoAttachment";
import { VoiceNotePlayer } from "./VoiceNotePlayer";

export function MessageAttachments({
  attachments,
  caption,
  alignEnd,
}: {
  attachments: readonly MessageAttachmentView[];
  caption: string | null;
  alignEnd: boolean;
}) {
  const { t } = useI18n();
  return (
    <ul className={cn("flex flex-col gap-2", alignEnd ? "items-end" : "items-start")} aria-label={t("conversationMedia.label")}>
      {attachments.map((attachment, index) => (
        <li key={index} className="max-w-full min-w-0" data-attachment={attachment.kind}>
          <Attachment attachment={attachment} caption={caption} />
        </li>
      ))}
    </ul>
  );
}

function Attachment({ attachment, caption }: { attachment: MessageAttachmentView; caption: string | null }) {
  if (attachment.kind === "audio") {
    return <VoiceAttachment attachment={attachment} />;
  }
  if (attachment.kind === "image" && hasStoredFile(attachment)) {
    return <PhotoAttachment mediaId={attachment.media_id} caption={caption} />;
  }
  if (attachment.kind === "location" && attachment.location) {
    return <PlaceAttachment location={attachment.location} mapUrl={attachment.map_url ?? null} />;
  }
  return (
    <AttachmentCard kind={attachment.kind}>
      <AttachmentNotes attachment={attachment} />
    </AttachmentCard>
  );
}

function AttachmentCard({ kind, aside, children }: { kind: AttachmentKind; aside?: ReactNode; children?: ReactNode }) {
  const { t } = useI18n();
  const Icon = ATTACHMENT_ICONS[kind];
  return (
    <div className="w-80 max-w-full space-y-2 rounded-2xl rounded-bl-md bg-surface-muted px-4 py-3 text-ink">
      <p className="flex items-center gap-2 text-sm font-medium">
        <Icon className="size-4 shrink-0 text-ink-muted" aria-hidden />
        <span className="min-w-0 flex-1">{t(ATTACHMENT_KIND_LABELS[kind])}</span>
        {aside}
      </p>
      {children}
    </div>
  );
}

function AttachmentNotes({ attachment }: { attachment: MessageAttachmentView }) {
  const { t } = useI18n();
  return (
    <>
      {attachment.is_media_deleted ? <p className="text-xs text-ink-muted">{t("conversationMedia.deleted")}</p> : null}
      {attachment.problem ? (
        <p className="flex items-start gap-1.5 text-xs text-ink-muted">
          <IconAlert className="mt-px size-3.5 shrink-0 text-warning" aria-hidden />
          <span>{t(ATTACHMENT_PROBLEMS[attachment.problem])}</span>
        </p>
      ) : null}
    </>
  );
}

function VoiceAttachment({ attachment }: { attachment: MessageAttachmentView }) {
  const { t } = useI18n();
  const duration = voiceDuration(attachment);
  const transcript = voiceTranscript(attachment);
  return (
    <AttachmentCard
      kind="audio"
      aside={
        duration ? (
          <span className="text-xs font-normal text-ink-subtle tabular-nums" dir="ltr">
            {duration}
          </span>
        ) : null
      }
    >
      {hasStoredFile(attachment) ? <VoiceNotePlayer mediaId={attachment.media_id} /> : null}
      {transcript ? (
        <div>
          <p className="text-xs font-medium text-ink-subtle">{t("conversationMedia.voice.transcript")}</p>
          <p dir="auto" className="text-[0.9375rem] leading-6 break-words whitespace-pre-wrap">
            {transcript}
          </p>
        </div>
      ) : null}
      <AttachmentNotes attachment={attachment} />
    </AttachmentCard>
  );
}

function PlaceAttachment({ location, mapUrl }: { location: SharedLocation; mapUrl: string | null }) {
  const { t } = useI18n();
  const title = placeTitle(location);
  const subtitle = placeSubtitle(location);
  const link = safeMapUrl(mapUrl);
  const coordinates = formatCoordinates(location);
  return (
    <AttachmentCard kind="location">
      <div className="space-y-0.5">
        <p dir="auto" className="text-[0.9375rem] leading-6 font-medium break-words">
          {title ?? t("conversationMedia.place.unnamed")}
        </p>
        {subtitle ? (
          <p dir="auto" className="text-sm break-words text-ink-muted">
            {subtitle}
          </p>
        ) : null}
        <p dir="ltr" className="text-xs text-ink-subtle tabular-nums">
          {coordinates}
        </p>
      </div>
      {link ? (
        <a
          href={link}
          target="_blank"
          rel="noopener noreferrer"
          aria-label={t("conversationMedia.place.openMapLabel", { place: title ?? coordinates })}
          className="inline-flex items-center gap-1.5 rounded-md text-sm font-medium text-accent underline-offset-4 hover:underline focus-visible:outline-2 focus-visible:outline-focus pointer-coarse:min-h-11"
        >
          {t("conversationMedia.place.openMap")}
          <IconExternal className="size-4" aria-hidden />
        </a>
      ) : null}
    </AttachmentCard>
  );
}
