import { SectionLoading } from "@/components/business/SectionLoading";
import { Skeleton } from "@/components/ui";

import { BookingDaysSkeleton } from "./_components/BookingsSkeleton";

export default function BookingsLoading() {
  return (
    <SectionLoading page="bookings" label="bookings.loading">
      <div className="space-y-5">
        <div className="flex flex-wrap gap-3">
          <Skeleton className="h-9 w-full max-w-lg rounded-xl" />
          <Skeleton className="h-9 w-40 rounded-lg" />
        </div>
        <BookingDaysSkeleton days={2} />
      </div>
    </SectionLoading>
  );
}
