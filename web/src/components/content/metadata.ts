import { getI18n } from "@/i18n/server";
import type { MessageKey } from "@/i18n/translate";
import { BUSINESS_SECTION_LABELS, type BusinessSection } from "@/lib/navigation";

/**
 * Metadata of a section's sub-page: "Unanswered questions · Knowledge"
 * (the business layout appends the business name).
 *
 *     export const generateMetadata = subPageMetadata("knowledge", "knowledge.tabs.questions");
 */
export function subPageMetadata(section: BusinessSection, page: MessageKey) {
  return async () => {
    const { t } = await getI18n();
    return { title: `${t(page)} · ${t(BUSINESS_SECTION_LABELS[section])}` };
  };
}
