"use client";

import { useState } from "react";

import { useBusiness } from "@/components/business/BusinessContext";
import { IconImage } from "@/components/icons";
import { Modal } from "@/components/ui";
import { useI18n } from "@/i18n/client";

import { messageMediaUrl } from "../../_lib/messageMedia";

/**
 * A photo a customer sent: a thumbnail in the transcript that opens the
 * whole picture. It is loaded through the BFF with the session (each
 * opening is in the audit log), so it is a plain image element: the Next.js
 * image optimizer cannot fetch a private file. A photo that cannot be shown
 * (deleted, session ended) leaves a placeholder that says so.
 */
export function PhotoAttachment({ mediaId, caption }: { mediaId: string; caption: string | null }) {
  const { t } = useI18n();
  const { business } = useBusiness();
  const [isOpen, setOpen] = useState(false);
  const [isBroken, setBroken] = useState(false);
  const url = messageMediaUrl(business.id, mediaId);
  const alt = caption ? t("conversationMedia.photo.altWithCaption", { caption }) : t("conversationMedia.photo.alt");

  if (isBroken) {
    return (
      <p className="flex items-center gap-2 rounded-xl border border-dashed border-line-strong px-3 py-2.5 text-sm text-ink-muted" role="note">
        <IconImage className="size-5 shrink-0" aria-hidden />
        {t("conversationMedia.photo.unavailable")}
      </p>
    );
  }

  return (
    <>
      <button
        type="button"
        onClick={() => setOpen(true)}
        aria-label={t("conversationMedia.photo.open")}
        aria-haspopup="dialog"
        className="block overflow-hidden rounded-xl border border-line bg-surface-muted transition-opacity hover:opacity-90"
      >
        {/* eslint-disable-next-line @next/next/no-img-element -- a private, audited file the optimizer cannot fetch */}
        <img
          src={url}
          alt={alt}
          loading="lazy"
          decoding="async"
          onError={() => setBroken(true)}
          className="block max-h-60 w-auto max-w-full object-contain"
        />
      </button>
      <Modal open={isOpen} onClose={() => setOpen(false)} title={t("conversationMedia.photo.viewerTitle")} size="xl">
        <figure className="space-y-3">
          {/* eslint-disable-next-line @next/next/no-img-element -- the same private file, full size */}
          <img src={url} alt={alt} className="mx-auto block max-h-[70dvh] w-auto max-w-full rounded-lg object-contain" />
          {caption ? (
            <figcaption dir="auto" className="text-sm text-ink-muted">
              {caption}
            </figcaption>
          ) : null}
        </figure>
      </Modal>
    </>
  );
}
