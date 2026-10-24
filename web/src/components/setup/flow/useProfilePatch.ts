"use client";

/**
 * Autosave of the profile from the tunnel: PATCH …/profile with only the
 * fields a screen changed (answers name only their own questions, so the
 * others stay as they are). Resolves to whether it was saved; the top bar
 * says so ("Saved" / "Not saved yet").
 */

import { useCallback } from "react";

import { api } from "@/api/client";
import { unwrap } from "@/api/result";
import type { RequestBody } from "@/api/types";

export type ProfilePatch = RequestBody<"/v1/businesses/{business_id}/profile", "patch">;

export function useProfilePatch(businessId: string) {
  return useCallback(
    async (patch: ProfilePatch): Promise<boolean> => {
      try {
        await unwrap(api.PATCH("/v1/businesses/{business_id}/profile", { params: { path: { business_id: businessId } }, body: patch }));
        return true;
      } catch {
        return false;
      }
    },
    [businessId],
  );
}
