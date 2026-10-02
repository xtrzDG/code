"use client";

import { createContext, useContext } from "react";

import type { ApiQuery } from "@/api/hooks";
import type { AssistantVersionSummary } from "@/lib/assistant/versions";

export interface AssistantContextValue {
  /** The version history (newest first), shared by every Assistant sub-page. */
  versions: ApiQuery<AssistantVersionSummary[]>;
  /** Opens "Build a new version" (owners). */
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
