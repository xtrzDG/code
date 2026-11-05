import { SectionLoading } from "@/components/business/SectionLoading";
import { SkeletonCardList } from "@/components/ui";

export default function SegmentsLoading() {
  return (
    <SectionLoading page="customers/segments" label="segments.loading">
      <SkeletonCardList cards={2} />
    </SectionLoading>
  );
}
