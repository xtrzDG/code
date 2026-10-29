"use client";

/**
 * The business's own settings (its name, city, languages, time zone) in
 * the edit mode, saved by themselves like the profile: a moment after the
 * owner stops typing and when the screen goes away. The save is the
 * tunnel's (useBusinessSave: the revision shown, read again on a
 * conflict, a toast when it fails).
 */

import { useCallback, useEffect, useRef } from "react";

import type { BusinessChanges, useBusinessSave } from "../flow/useBusinessSave";
import { useAutosave } from "../useAutosave";
import type { FieldSaveOptions } from "./useProfileField";

type BusinessSave = ReturnType<typeof useBusinessSave>;

export function useBusinessField<T>(business: BusinessSave, value: T, toChanges: (value: T) => BusinessChanges, options: FieldSaveOptions<T> = {}) {
  const build = useRef(toChanges);
  useEffect(() => {
    build.current = toChanges;
  });
  const { save: saveBusiness } = business;
  const save = useCallback(async (current: T) => (await saveBusiness(() => build.current(current))) !== null, [saveBusiness]);
  return useAutosave(value, save, { ...options, flushOnLeave: true });
}
