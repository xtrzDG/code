/**
 * Texts of the business profile, English: the reference. `onboarding.*`
 * holds the profile's words other pages share (kinds of offer, what is
 * booked, the week editor, "what to add" counts); `profileEdit.*` is
 * Assistant → Business profile, the section cards and the editors that
 * save as the owner types. Spread into en.ts; ru.ts and ka.ts spread
 * their own translations.
 */

import { profileEditEn } from "./profileEdit.en";

export const onboardingEn = {
  onboarding: {
    choose: "Choose…",
    gaps: {
      times: { one: "{count} time", other: "{count} times" },
      notReady: { one: "{count} required item is missing", other: "{count} required items are missing" },
    },
    week: {
      closed: "Closed",
      opens: "Opens",
      closes: "Closes",
      addInterval: "Add a break or second shift",
      removeInterval: "Remove interval",
      overnight: "until {time} the next day",
      roundTheClock: "Open 24 hours",
      copyToAll: "Copy Monday to every day",
    },
    offer: {
      kinds: {
        faq: "Question and answer",
        policy: "Rule",
        menu_item: "Menu item",
        service: "Service",
        room_type: "Room type",
        package: "Package",
        vehicle: "Vehicle",
        product: "Product",
      },
    },
    booking: {
      noBookings: "Your niche does not take bookings: the assistant collects requests and passes them to the manager.",
      resourceKinds: {
        table: "Table",
        room: "Room",
        staff: "Specialist",
        arena: "Arena or hall",
        bay: "Service bay",
        vehicle: "Vehicle",
        slot: "Time slot",
      },
    },
    resources: {
      namePlaceholder: "For example: Arena 1",
    },
  },
  profileEdit: profileEditEn,
} as const;
