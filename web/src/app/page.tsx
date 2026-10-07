import { redirect } from "next/navigation";

import { getLocale } from "@/i18n/server";
import { HOME_PATH } from "@/lib/navigation";
import { localeHomePath } from "@/lib/publicSite/paths";
import { hasSession } from "@/server/api";

/**
 * "/": signed-in users go straight to their businesses; visitors to the
 * public page in their language (the cookie, else the browser's
 * languages): "/ru", with the query kept ("/ru?country=GE"). It is the
 * x-default of the public pages' hreflang alternates.
 */
export default async function RootPage({ searchParams }: PageProps<"/">) {
  if (await hasSession()) {
    redirect(HOME_PATH);
  }
  const [locale, query] = await Promise.all([getLocale(), searchParams]);
  const search = new URLSearchParams();
  for (const [key, value] of Object.entries(query)) {
    for (const item of Array.isArray(value) ? value : value === undefined ? [] : [value]) {
      search.append(key, item);
    }
  }
  const suffix = search.size > 0 ? `?${search.toString()}` : "";
  redirect(`${localeHomePath(locale)}${suffix}`);
}
