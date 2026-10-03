"use client";

import { createContext, useContext } from "react";

import type { Query } from "@/api/useQuery";
import type { AssistantVersionSummary } from "@/lib/assistant/versions";

export interface AssistantContextValue {
  /** The version history (newest first), shared by every Assistant sub-page. */
  versions: Query<AssistantVersionSummary[]>;
  /** Opens "Build a new version" (owners, under Advanced: the versions page). */
  openBuild: () => void;
}

export const AssistantContext = createContext<AssistantContextValue | null>(null);

export function useAssistant(): AssistantContextValue {
  const value = useContext(AssistantContext);
  if (!value) {
    throw new Error("useAssistant() must be used inside the Assistant section.");
  }
  return value;
}
