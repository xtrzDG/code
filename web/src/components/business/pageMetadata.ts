import { getI18n } from "@/i18n/server";
import type { MessageKey } from "@/i18n/translate";
import type { BusinessPage } from "@/lib/navigation";
import { pageTitleKeys } from "@/lib/sections";

/**
 * A business page's `generateMetadata`: "Quick replies · Settings" (the
 * business layout appends the business name); `detail` goes in front
 * ("Version · Versions and autotests · Assistant").
 *
 *     export const generateMetadata = pageMetadata("settings/quick-replies");
 */
export function pageMetadata(page: BusinessPage, detail?: MessageKey) {
  return async () => {
    const { t } = await getI18n();
    const keys = detail ? [detail, ...pageTitleKeys(page)] : pageTitleKeys(page);
    return { title: keys.map((key) => t(key)).join(" · ") };
  };
}
