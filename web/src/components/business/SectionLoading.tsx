import type { ReactNode } from "react";

import { LoadingRegion, PageHeader } from "@/components/ui";
import { getI18n } from "@/i18n/server";
import type { MessageKey } from "@/i18n/translate";
import { BUSINESS_SECTION_LABELS, type BusinessSection } from "@/lib/navigation";

/**
 * A section's `loading.tsx`: its real title at once, and skeletons shaped
 * like its content (the `children`) until the page arrives.
 *
 *     export default function Loading() {
 *       return <SectionLoading section="leads" label="leads.loading"><SkeletonCardList /></SectionLoading>;
 *     }
 */
export async function SectionLoading({
  section,
  label,
  children,
}: {
  section: Exclude<BusinessSection, "onboarding">;
  /** What is loading, for screen readers. */
  label: MessageKey;
  children: ReactNode;
}) {
  const { t } = await getI18n();
  return (
    <>
      <PageHeader title={t(BUSINESS_SECTION_LABELS[section])} description={t(`pages.${section}.description`)} />
      <LoadingRegion label={t(label)}>{children}</LoadingRegion>
    </>
  );
}
