/**
 * Loading a call recording for the player in one request.
 *
 * The player plays the downloaded file from memory (an object URL): it can
 * seek anywhere, Safari and iOS play it, and the API writes one audit entry
 * per playback. Unlike the media element, a fetch also sees the status, so
 * an expired session, a deleted recording and an unreachable service are
 * told apart.
 */

export type RecordingLoadFailure = "expired" | "missing" | "unavailable";

export type RecordingLoad = { ok: true; blob: Blob } | { ok: false; failure: RecordingLoadFailure };

export async function loadRecording(url: string, fetchImpl: typeof fetch = fetch): Promise<RecordingLoad> {
  try {
    const response = await fetchImpl(url, { credentials: "same-origin", cache: "no-store" });
    if (response.status === 401) {
      return { ok: false, failure: "expired" };
    }
    if (response.status === 404) {
      return { ok: false, failure: "missing" };
    }
    if (!response.ok) {
      return { ok: false, failure: "unavailable" };
    }
    return { ok: true, blob: await response.blob() };
  } catch {
    return { ok: false, failure: "unavailable" };
  }
}
