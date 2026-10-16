"use client";

/**
 * One part of the profile in the edit mode, saved by itself: PATCH
 * …/profile with what `toPatch` makes of the value, a moment after the
 * owner stops typing and when the screen goes away. The API's refusal is
 * kept, so the screen can say under the field what is wrong ("This is not
 * a phone number"); the next save that goes through clears it.
 */

import { useCallback, useEffect, useRef, useState } from "react";

import { api } from "@/api/client";
import { isApiError, type ApiError } from "@/api/errors";
import { unwrap } from "@/api/result";

import type { ProfilePatch } from "../flow/useProfilePatch";
import { useAutosave } from "../useAutosave";

export interface FieldSaveOptions<T> {
  isValid?: (value: T) => boolean;
  enabled?: boolean;
}

export function useProfileField<T>(businessId: string, value: T, toPatch: (value: T) => ProfilePatch, options: FieldSaveOptions<T> = {}) {
  const [error, setError] = useState<ApiError | null>(null);
  const build = useRef(toPatch);
  useEffect(() => {
    build.current = toPatch;
  });

  const save = useCallback(
    async (current: T): Promise<boolean> => {
      try {
        await unwrap(api.PATCH("/v1/businesses/{business_id}/profile", { params: { path: { business_id: businessId } }, body: build.current(current) }));
        setError(null);
        return true;
      } catch (caught) {
        setError(isApiError(caught) ? caught : null);
        return false;
      }
    },
    [businessId],
  );

  const autosave = useAutosave(value, save, { ...options, flushOnLeave: true });
  return { error, flush: autosave.flush };
}
