import { IconSparkles } from "@/components/icons";
import { Card, EmptyState, PageHeader } from "@/components/ui";
import { getI18n } from "@/i18n/server";
import { BUSINESS_SECTION_LABELS, type BusinessSection } from "@/lib/navigation";

type PlaceholderSection = Exclude<BusinessSection, "onboarding">;

/**
 * Server Component placeholder for a cabinet section that is not built yet:
 * the page title, its description and a "coming soon" note.
 */
export async function SectionPlaceholder({ section }: { section: PlaceholderSection }) {
  const { t } = await getI18n();
  return (
    <>
      <PageHeader title={t(BUSINESS_SECTION_LABELS[section])} description={t(`pages.${section}.description`)} />
      <Card>
        <EmptyState icon={<IconSparkles className="size-6" />} title={t(BUSINESS_SECTION_LABELS[section])} description={t("common.comingSoon")} />
      </Card>
    </>
  );
}

/** `export const generateMetadata = sectionMetadata("bookings");` */
export function sectionMetadata(section: BusinessSection) {
  return async () => {
    const { t } = await getI18n();
    return { title: t(BUSINESS_SECTION_LABELS[section]) };
  };
}
