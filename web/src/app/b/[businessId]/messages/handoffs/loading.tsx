import { SectionLoading } from "@/components/business/SectionLoading";
import { Skeleton, SkeletonCardList } from "@/components/ui";

export default function HandoffsLoading() {
  return (
    <SectionLoading page="messages/handoffs" label="handoffs.loading">
      <div className="space-y-5">
        <Skeleton className="h-10 w-full max-w-sm rounded-xl" />
        <SkeletonCardList cards={3} />
      </div>
    </SectionLoading>
  );
}
