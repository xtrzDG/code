"use client";

import { createContext, useContext } from "react";

import type { BrandView } from "../_lib/brands";

export interface BrandFrameValue {
  brand: BrandView;
  /** The person runs the brand (team, locations, shared answers). */
  isOwner: boolean;
}

export const BrandFrameContext = createContext<BrandFrameValue | null>(null);

/** The open brand, for the pages inside its frame. */
export function useBrandFrame(): BrandFrameValue {
  const value = useContext(BrandFrameContext);
  if (value === null) {
    throw new Error("useBrandFrame is used outside a brand's pages.");
  }
  return value;
}
