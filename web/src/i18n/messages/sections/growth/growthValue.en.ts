/**
 * `growthValue.*` texts: the bookings the waitlist filled and those the
 * return-visit messages brought back, as their own lines of the value
 * hero and the reports, in English: the reference that ru and ka are
 * typed against.
 */

export const growthValueEn = {
  label: "Bookings the assistant won back",
  waitlist: { one: "{count} from the waitlist", other: "{count} from the waitlist" },
  campaign: { one: "{count} after a return-visit message", other: "{count} after return-visit messages" },
  worth: "≈ {money}",
  waitlistHint: "Freed places taken by customers who were waiting.",
  campaignHint: "Customers who booked again after the message.",
  rows: {
    waitlistBookings: "Bookings from the waitlist",
    waitlistValue: "Worth of bookings from the waitlist",
    campaignBookings: "Bookings after return-visit messages",
    campaignValue: "Worth of bookings after return-visit messages",
  },
} as const;
