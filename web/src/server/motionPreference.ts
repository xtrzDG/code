import "server-only";

import { cookies } from "next/headers";

import { MOTION_COOKIE, parseMotionPreference, type MotionPreference } from "@/lib/motionPreference";

/** How much the site moves for this request's person (the `aw_motion` cookie, else as the device asks). */
export async function getMotionPreference(): Promise<MotionPreference> {
  return parseMotionPreference((await cookies()).get(MOTION_COOKIE)?.value);
}
