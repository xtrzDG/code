"use client";

import { useCallback, useEffect, useEffectEvent, useRef, useState } from "react";

import { LiveEventStream, type LiveStreamStatus } from "@/api/events";
import { everythingOf, invalidationsFor, type LiveEvent } from "@/api/liveEvents";
import { LiveInvalidation } from "@/api/liveInvalidation";
import { queryKeys } from "@/api/queryKeys";

export interface LiveStreamState {
  status: LiveStreamStatus;
  /** Try to connect again now (after a dropped connection). */
  reconnect: () => void;
}

/**
 * The business's live event stream while `enabled`: every event makes the
 * lists it touches out of date (they reload if shown), a resync reloads
 * everything, and `onEvent` hears each change (the chime, the toast). The
 * stream reconnects by itself, and at once when the browser is back online.
 * A page put away in the back/forward cache closes its stream (an open one
 * would hold one of the browser's few connections to the cabinet) and
 * resumes it, from the last event, when it is shown again.
 */
export function useLiveStream(
  businessId: string,
  enabled: boolean,
  onEvent: (event: LiveEvent) => void,
): LiveStreamState {
  const [status, setStatus] = useState<LiveStreamStatus>("connecting");
  const streamRef = useRef<LiveEventStream | null>(null);
  const heard = useEffectEvent((event: LiveEvent) => onEvent(event));

  useEffect(() => {
    if (!enabled) {
      return;
    }
    const invalidation = new LiveInvalidation({ alwaysFresh: [queryKeys.inbox.all(businessId)] });
    const stream = new LiveEventStream({
      businessId,
      onEvent: (event) => {
        invalidation.add(invalidationsFor(event, businessId));
        heard(event);
      },
      onResync: () => invalidation.add(everythingOf(businessId)),
      onStatus: setStatus,
    });
    streamRef.current = stream;
    const onOnline = () => stream.reconnectNow();
    const onVisible = () => invalidation.resume();
    const onPageHide = () => stream.stop();
    const onPageShow = (event: PageTransitionEvent) => {
      if (event.persisted) {
        stream.start();
      }
    };
    window.addEventListener("online", onOnline);
    document.addEventListener("visibilitychange", onVisible);
    window.addEventListener("pagehide", onPageHide);
    window.addEventListener("pageshow", onPageShow);
    stream.start();
    return () => {
      window.removeEventListener("online", onOnline);
      document.removeEventListener("visibilitychange", onVisible);
      window.removeEventListener("pagehide", onPageHide);
      window.removeEventListener("pageshow", onPageShow);
      stream.stop();
      invalidation.dispose();
      streamRef.current = null;
    };
  }, [businessId, enabled]);

  const reconnect = useCallback(() => streamRef.current?.reconnectNow(), []);
  return { status: enabled ? status : "stopped", reconnect };
}
