"use client";

/**
 * The palette's door for a pointer or a thumb: a search button (the
 * phone's top bar, the sidebar). Its name tells the shortcut, so keyboard
 * users learn Cmd/Ctrl+K from it.
 */

import { IconSearch } from "@/components/icons";
import { useI18n } from "@/i18n/client";
import { cn } from "@/lib/cn";

import { useCommandPalette } from "./CommandPaletteProvider";

export function CommandPaletteButton({ className }: { className?: string }) {
  const { t } = useI18n();
  const palette = useCommandPalette();
  if (!palette) {
    return null;
  }
  return (
    <button
      type="button"
      onClick={palette.open}
      aria-haspopup="dialog"
      aria-expanded={palette.isOpen}
      aria-keyshortcuts="Control+K Meta+K"
      aria-label={t("palette.open")}
      title={t("palette.openTitle")}
      className={cn(
        "motion-press flex size-11 shrink-0 cursor-pointer items-center justify-center rounded-full text-ink-muted hover:text-ink",
        className,
      )}
    >
      <IconSearch className="size-5" aria-hidden />
    </button>
  );
}
