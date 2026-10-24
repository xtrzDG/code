import "server-only";

import { cookies } from "next/headers";

import { VIEWER_TIME_ZONE_COOKIE, parseViewerTimeZone } from "@/lib/viewerTimeZone";

/** The reader's time zone remembered by the browser (`aw_tz`), or null before the first visit. */
export async function getViewerTimeZone(): Promise<string | null> {
  return parseViewerTimeZone((await cookies()).get(VIEWER_TIME_ZONE_COOKIE)?.value);
}
