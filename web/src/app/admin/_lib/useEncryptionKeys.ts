"use client";

import { useEffect } from "react";

import { api } from "@/api/client";
import { isApiError } from "@/api/errors";
import { queryKeys } from "@/api/queryKeys";
import { useMutation } from "@/api/useMutation";
import { useQuery } from "@/api/useQuery";

import { KEY_ROTATION_POLL_MS, isRotationRunning, type EncryptionKeys } from "./keyRotation";

/**
 * The key ring and its latest re-encryption run, polled while the worker
 * has not finished it, and the start of a new run (409 while one runs: the
 * page then shows that run).
 */
export function useEncryptionKeys() {
  const keys = useQuery(queryKeys.admin.encryptionKeys(), () => api.GET("/v1/admin/security/encryption-keys"), {
    staleMs: 0,
  });
  const start = useMutation(() => api.POST("/v1/admin/security/encryption-keys/rotate"), {
    errorToast: false,
  });
  const latest = keys.data?.latest_rotation ?? null;
  const isRunning = isRotationRunning(latest);
  const { reload, setData } = keys;

  useEffect(() => {
    if (!isRunning) {
      return;
    }
    const timer = window.setInterval(reload, KEY_ROTATION_POLL_MS);
    return () => window.clearInterval(timer);
  }, [isRunning, reload]);

  /** True when the run was queued; false (the error is in `start.error`) otherwise. */
  const begin = async (): Promise<boolean> => {
    const result = await start.run();
    if (!result.ok) {
      if (isApiError(result.error) && result.error.status === 409) {
        reload();
      }
      return false;
    }
    setData((current: EncryptionKeys | undefined) => ({
      key_count: current?.key_count ?? result.data.rotation.key_count,
      latest_rotation: result.data.rotation,
    }));
    return true;
  };

  return { keys, latest, isRunning, begin, isStarting: start.isPending, startError: start.error };
}
