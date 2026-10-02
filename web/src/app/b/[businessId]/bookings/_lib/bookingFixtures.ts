/** Test data shared by the bookings page's unit tests. */

import type { BookingView } from "@/components/insights/types";

export function booking(id: string, date: string, time: string | null): BookingView {
  return {
    id,
    business_id: "business_1",
    resource_id: "resource_1",
    resource_name: "Table",
    contact_id: "contact_1",
    contact_name: null,
    contact_phone_number: null,
    date,
    time,
    end_date: date,
    end_time: null,
    timezone: "Asia/Tbilisi",
    party_size: 2,
    status: "confirmed",
    source_channel: "phone",
    notes: null,
    is_sandbox: false,
    created_at: 1_790_000_000_000_000,
  };
}
