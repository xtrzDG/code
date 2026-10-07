"use client";

/**
 * Where the owner is in the tunnel, kept in the address (`?step=hours`):
 * a reload stays on the same screen, the browser's Back goes a step back,
 * and every move knows its direction (deeper or back out) for the depth
 * transition. Without `?step` the tunnel opens at `fallback`.
 */

import { usePathname, useRouter, useSearchParams } from "next/navigation";
import { useCallback, useState } from "react";

import { direction as directionOf, isTunnelPlace, type TunnelPlace } from "@/lib/tunnel/steps";

import { useTunnelTelemetry } from "./useTunnelTelemetry";

export function useTunnelPlace(fallback: TunnelPlace, allowed: (place: TunnelPlace) => boolean = () => true) {
  const router = useRouter();
  const pathname = usePathname();
  const requested = useSearchParams().get("step");
  const place: TunnelPlace = isTunnelPlace(requested) && allowed(requested) ? requested : fallback;

  // The direction of the last move: the place before is remembered in state.
  const [track, setTrack] = useState<{ place: TunnelPlace; direction: 1 | -1 | 0 }>({ place, direction: 0 });
  if (track.place !== place) {
    setTrack({ place, direction: directionOf(track.place, place) });
  }
  useTunnelTelemetry(place, pathname);

  const go = useCallback(
    (next: TunnelPlace, options: { replace?: boolean; path?: string } = {}) => {
      const target = `${options.path ?? pathname}?step=${next}`;
      if (options.replace) {
        router.replace(target, { scroll: false });
      } else {
        router.push(target, { scroll: false });
      }
      const calm = window.matchMedia("(prefers-reduced-motion: reduce)").matches;
      window.scrollTo({ top: 0, behavior: calm ? "auto" : "smooth" });
    },
    [pathname, router],
  );

  return { place, direction: track.direction, go };
}
