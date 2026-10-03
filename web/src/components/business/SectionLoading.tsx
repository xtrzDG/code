import type { ReactNode } from "react";

import { LoadingRegion, PageHeader } from "@/components/ui";
import { getI18n } from "@/i18n/server";
import type { MessageKey } from "@/i18n/translate";
import type { BusinessPage } from "@/lib/navigation";
import { PAGE_DESCRIPTIONS, pageLabel } from "@/lib/sections";

/**
 * A page's `loading.tsx`: its real title at once, and skeletons shaped
 * like its content (the `children`) until the page arrives. Inside a
 * section frame (Assistant, Settings) the title is the frame's
 * and this header shrinks to the page's description (see PageHeader).
 *
 *     export default function Loading() {
 *       return <SectionLoading page="settings/quick-replies" label="quickReplies.loading"><SkeletonCardList /></SectionLoading>;
 *     }
 */
export async function SectionLoading({
  page,
  label,
  children,
}: {
  page: BusinessPage;
  /** What is loading, for screen readers. */
  label: MessageKey;
  children: ReactNode;
}) {
  const { t } = await getI18n();
  const description = PAGE_DESCRIPTIONS[page];
  return (
    <>
      <PageHeader title={t(pageLabel(page))} description={description ? t(description) : undefined} />
      <LoadingRegion label={t(label)}>{children}</LoadingRegion>
    </>
  );
}
