"use client";

import { api } from "@/api/client";
import { queryKeys } from "@/api/queryKeys";
import { useMutation } from "@/api/useMutation";
import { useQuery } from "@/api/useQuery";
import { signOut } from "@/components/shell/signOut";
import { LOGIN_PATH } from "@/lib/navigation";
import { onlyCurrent, sortSessions, withoutSession } from "@/lib/security/devices";

/**
 * The person's signed-in devices (GET /v1/me/sessions), signing one out,
 * signing out everywhere else and everywhere (this device too); the list
 * follows each answer.
 */
export function useDevices() {
  const sessions = useQuery(queryKeys.account.sessions(), () => api.GET("/v1/me/sessions"), { staleMs: 0 });
  const end = useMutation(
    (sessionId: string) => api.DELETE("/v1/me/sessions/{session_id}", { params: { path: { session_id: sessionId } } }),
    { errorToast: false },
  );
  const endOthers = useMutation(() => api.POST("/v1/me/sessions/revoke-others"), { errorToast: false });
  const endAll = useMutation(() => api.POST("/v1/me/sessions/revoke-all"), { errorToast: false });
  const { setData } = sessions;

  const endOne = async (sessionId: string): Promise<boolean> => {
    const result = await end.run(sessionId);
    if (result.ok) {
      setData((current) => (current ? { items: withoutSession(current.items ?? [], sessionId) } : current));
    }
    return result.ok;
  };

  /** How many devices were signed out, or null when it failed. */
  const endEverywhereElse = async (): Promise<number | null> => {
    const result = await endOthers.run();
    if (!result.ok) {
      return null;
    }
    setData((current) => (current ? { items: onlyCurrent(current.items ?? []) } : current));
    return result.data.revoked_count;
  };

  /**
   * Every session ends, this one too: the cookie and this browser's traces
   * go, and the sign-in page loads in full. False when the API refused.
   */
  const endEverywhere = async (): Promise<boolean> => {
    const result = await endAll.run();
    if (!result.ok) {
      return false;
    }
    await signOut();
    window.location.assign(LOGIN_PATH);
    return true;
  };

  return {
    sessions,
    items: sortSessions(sessions.data?.items ?? []),
    endOne,
    isEnding: end.isPending,
    endError: end.error,
    endEverywhereElse,
    isEndingOthers: endOthers.isPending,
    endOthersError: endOthers.error,
    endEverywhere,
    isEndingAll: endAll.isPending,
    endAllError: endAll.error,
  };
}
