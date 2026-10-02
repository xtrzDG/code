import { SectionLoading } from "@/components/business/SectionLoading";
import { Skeleton, SkeletonCardList } from "@/components/ui";

export default function LeadsLoading() {
  return (
    <SectionLoading page="messages/leads" label="leads.loading">
      <div className="space-y-5">
        <Skeleton className="h-10 w-full max-w-xl rounded-xl" />
        <SkeletonCardList cards={4} />
      </div>
    </SectionLoading>
  );
}
