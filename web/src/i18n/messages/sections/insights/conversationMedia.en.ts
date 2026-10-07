/**
 * `conversationMedia.*` texts of what customers send besides text (voice
 * messages, photos, places, stickers, files), in English: the reference that
 * ru and ka are typed against.
 */

export const conversationMediaEn = {
  label: "Attachments",
  kinds: {
    audio: "Voice message",
    image: "Photo",
    location: "Location",
    contact: "Contact card",
    sticker: "Sticker",
    file: "File",
  },
  voice: {
    transcript: "Transcript",
    play: "Play",
    playLabel: "Play the voice message",
    playerLabel: "Voice message from the customer",
    playerUnsupported: "Your browser cannot play audio here.",
    loading: "Loading…",
    missing: "This voice message is no longer available: it was deleted after the retention period or with the customer's data.",
    error: "The voice message could not be loaded. Try again in a minute.",
    retry: "Try again",
  },
  photo: {
    alt: "Photo sent by the customer",
    altWithCaption: "Photo sent by the customer: {caption}",
    open: "Open the photo",
    viewerTitle: "Photo from the customer",
    unavailable: "The photo could not be shown: it was deleted, or your session has ended.",
  },
  place: {
    openMap: "Open in maps",
    openMapLabel: "Open {place} in maps (opens in a new tab)",
    unnamed: "Shared location",
  },
  deleted: "The file was deleted after the retention period.",
  problems: {
    unsupported_kind: "The assistant can't read this and asked the customer to write instead.",
    too_large: "Too large to open: the customer was asked to write instead.",
    too_long: "Too long to transcribe: the customer was asked to write instead.",
    unavailable: "The messenger no longer had this file: the customer was asked to write instead.",
    unrecognized_format: "Not a format the assistant reads: the customer was asked to write instead.",
    not_understood: "No words could be made out: the customer was asked to write instead.",
  },
} as const;
