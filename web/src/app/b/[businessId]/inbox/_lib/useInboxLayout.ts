"use client";

/**
 * The person's layout of the inbox (lib inboxLayout.ts), remembered in this
 * browser for them: the row density and the list column's width, with the
 * width shown live while the edge is dragged.
 */

import { useState } from "react";

import { useBusiness } from "@/components/business/BusinessContext";
import { useUserPreference } from "@/lib/useUserPreference";

import { DENSITY_PREFERENCE, LIST_WIDTH_PREFERENCE, parseDensity, parseListWidth, type InboxDensity } from "./inboxLayout";

export function useInboxLayout() {
  const { me } = useBusiness();
  const [storedDensity, setStoredDensity] = useUserPreference(DENSITY_PREFERENCE, me.user.id);
  const [storedWidth, setStoredWidth] = useUserPreference(LIST_WIDTH_PREFERENCE, me.user.id);
  const [dragWidth, setDragWidth] = useState<number | null>(null);

  return {
    density: parseDensity(storedDensity),
    setDensity: (density: InboxDensity) => setStoredDensity(density),
    /** The column's width in px; null keeps the responsive default. */
    listWidth: dragWidth ?? parseListWidth(storedWidth),
    previewWidth: setDragWidth,
    commitWidth: (width: number) => {
      setDragWidth(null);
      setStoredWidth(String(width));
    },
    resetWidth: () => {
      setDragWidth(null);
      setStoredWidth(null);
    },
  };
}
