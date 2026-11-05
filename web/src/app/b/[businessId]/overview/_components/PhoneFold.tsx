"use client";

/**
 * The Overview's folded rows on a phone (PhoneFold of the UI kit): which of
 * them a person opened is remembered for them in this browser
 * (`overview-open`), as the inbox remembers its density.
 */

import type { ReactNode } from "react";

import { useBusiness } from "@/components/business/BusinessContext";
import { PhoneFolds } from "@/components/ui";

const OPEN_FOLDS_PREFERENCE = "overview-open";

/** The remembered open rows for every PhoneFold of the Overview. */
export function OverviewFolds({ children }: { children: ReactNode }) {
  const { me } = useBusiness();
  return (
    <PhoneFolds preference={OPEN_FOLDS_PREFERENCE} userId={me.user.id}>
      {children}
    </PhoneFolds>
  );
}
