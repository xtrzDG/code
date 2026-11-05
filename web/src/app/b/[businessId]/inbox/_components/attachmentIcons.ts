/** The icon of each kind of attachment, in the transcript and in the inbox list. */

import type { ComponentType } from "react";

import { IconContactCard, IconFile, IconImage, IconMapPin, IconMic, IconSticker, type IconProps } from "@/components/icons";

import type { AttachmentKind } from "../_lib/messageMedia";

export const ATTACHMENT_ICONS: Record<AttachmentKind, ComponentType<IconProps>> = {
  audio: IconMic,
  image: IconImage,
  location: IconMapPin,
  contact: IconContactCard,
  sticker: IconSticker,
  other: IconFile,
};
