/**
 * `assistantControls.*` texts of Settings → General's assistant controls
 * card (an owner's kill switches: hand every customer to the team, switch
 * single actions off), in English: the reference that it is typed against.
 */

export const assistantControlsEn = {
  title: "Assistant controls",
  description: "Stop the assistant at once when it misbehaves: a change applies from the next message.",
  handOver: {
    label: "Pass every customer to the team",
    hint: "New messages wait for your team in the inbox, and calls go to your forwarding number.",
  },
  actions: {
    title: "What the assistant may do",
    hint: "A switched-off action is refused; the assistant takes a request or passes the customer to a colleague instead.",
    allOn: "All on",
    someOff: "Some off",
    create_booking: "Make bookings",
    reschedule_booking: "Move bookings",
    cancel_booking: "Cancel bookings",
    join_waitlist: "Add customers to the waitlist",
    create_lead: "Take requests and orders",
    send_link: "Send links",
    send_payment_link: "Send deposit payment links",
  },
  ownerOnly: "Only owners can change this.",
  handedOver: "Every customer now goes to your team",
  resumed: "The assistant answers on its own again",
  actionOff: "Action switched off",
  actionOn: "Action switched on",
} as const;
