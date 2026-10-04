/**
 * Pure rules of what customers send besides text: where the cabinet loads a
 * voice message or photo (the BFF, which writes an audit entry per opening),
 * how each kind is named, what the assistant could not read and why, and how
 * a shared place is described.
 */

import { BFF_BASE_PATH } from "@/api/client";
import type { Schema } from "@/api/types";
import type { MessageKey } from "@/i18n/translate";

import { formatCallDuration } from "./conversationModel";

export type AttachmentKind = Schema<"AttachmentKind">;
export type AttachmentProblem = Schema<"AttachmentProblem">;
export type MessageAttachmentView = Schema<"MessageAttachmentView">;
export type SharedLocation = Schema<"SharedLocation">;

export const ATTACHMENT_KIND_LABELS: Record<AttachmentKind, MessageKey> = {
  audio: "conversationMedia.kinds.audio",
  image: "conversationMedia.kinds.image",
  location: "conversationMedia.kinds.location",
  contact: "conversationMedia.kinds.contact",
  sticker: "conversationMedia.kinds.sticker",
  other: "conversationMedia.kinds.file",
};

export const ATTACHMENT_PROBLEMS: Record<AttachmentProblem, MessageKey> = {
  unsupported_kind: "conversationMedia.problems.unsupported_kind",
  too_large: "conversationMedia.problems.too_large",
  too_long: "conversationMedia.problems.too_long",
  unavailable: "conversationMedia.problems.unavailable",
  unrecognized_format: "conversationMedia.problems.unrecognized_format",
  not_understood: "conversationMedia.problems.not_understood",
};

const COORDINATE_DIGITS = 5;

/** The file of a voice message or photo, through the BFF (audited by the API). */
export function messageMediaUrl(businessId: string, mediaId: string): string {
  return `${BFF_BASE_PATH}/v1/businesses/${encodeURIComponent(businessId)}/media/${encodeURIComponent(mediaId)}`;
}

/** "0:07" for a voice message of seven seconds; null when the length is unknown. */
export function voiceDuration(attachment: MessageAttachmentView): string | null {
  const seconds = attachment.duration_seconds;
  return seconds === null || seconds === undefined ? null : formatCallDuration(seconds);
}

/** A voice message or photo the cabinet can still open. */
export function hasStoredFile(attachment: MessageAttachmentView): attachment is MessageAttachmentView & { media_id: string } {
  return Boolean(attachment.media_id) && !attachment.is_media_deleted;
}

/** The words of a voice message the assistant read; null without any. */
export function voiceTranscript(attachment: MessageAttachmentView): string | null {
  const text = attachment.transcript?.trim() ?? "";
  return text === "" ? null : text;
}

/** "41.69344, 44.80153": the coordinates in a fixed, language-neutral form. */
export function formatCoordinates(location: SharedLocation): string {
  return `${location.latitude.toFixed(COORDINATE_DIGITS)}, ${location.longitude.toFixed(COORDINATE_DIGITS)}`;
}

/** The place's name, its address, or null when the customer shared only coordinates. */
export function placeTitle(location: SharedLocation): string | null {
  const name = location.name?.trim();
  if (name) {
    return name;
  }
  const address = location.address?.trim();
  return address ? address : null;
}

/** The address under the name, when both are known and differ. */
export function placeSubtitle(location: SharedLocation): string | null {
  const name = location.name?.trim();
  const address = location.address?.trim();
  return name && address && address !== name ? address : null;
}

/**
 * A link that opens on a map: only an http(s) address is used, so a link
 * the API did not make cannot run anything in the cabinet.
 */
export function safeMapUrl(url: string | null | undefined): string | null {
  if (!url) {
    return null;
  }
  try {
    const parsed = new URL(url);
    return parsed.protocol === "https:" || parsed.protocol === "http:" ? parsed.toString() : null;
  } catch {
    return null;
  }
}

/** The attachments a message shows, in the order the customer sent them. */
export function messageAttachments(message: { attachments?: MessageAttachmentView[] | null }): MessageAttachmentView[] {
  return message.attachments ?? [];
}
