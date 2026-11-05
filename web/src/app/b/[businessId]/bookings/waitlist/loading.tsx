import { SectionLoading } from "@/components/business/SectionLoading";
import { SkeletonCardList } from "@/components/ui";

export default function WaitlistLoading() {
  return (
    <SectionLoading page="bookings/waitlist" label="waitlist.loading">
      <SkeletonCardList cards={3} />
    </SectionLoading>
  );
}
