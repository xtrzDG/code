"use client";

import { createContext, useContext, type ReactNode } from "react";

import type { UserMembershipView } from "@/api/types";

interface BrandsContextValue {
  /** Every business the person works in, with its brand (from GET /v1/me). */
  memberships: readonly UserMembershipView[];
  /** The signed-in person ("You" on the team, "Leave" instead of "Remove"). */
  userId: string;
}

const BrandsContext = createContext<BrandsContextValue | null>(null);

export function BrandsProvider({ memberships, userId, children }: BrandsContextValue & { children: ReactNode }) {
  return <BrandsContext.Provider value={{ memberships, userId }}>{children}</BrandsContext.Provider>;
}

export function useBrandsContext(): BrandsContextValue {
  const value = useContext(BrandsContext);
  if (value === null) {
    throw new Error("useBrandsContext is used outside /brands.");
  }
  return value;
}
