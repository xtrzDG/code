import { redirect } from "next/navigation";

import { HOME_PATH, LOGIN_PATH } from "@/lib/navigation";
import { hasSession } from "@/server/api";

/** "/" opens the businesses of a signed-in user, else the sign-in page. */
export default async function RootPage() {
  redirect((await hasSession()) ? HOME_PATH : LOGIN_PATH);
}
