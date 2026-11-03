/**
 * `assistantControls.*` texts of Settings → General's assistant controls
 * card (an owner's kill switches: hand every customer to the team, switch
 * single actions off), in English: the reference that it is typed against.
 */

export const assistantControlsEn = {
  title: "Assistant controls",
  description:
    "Stop the assistant from acting on its own, at once: the change applies from the next message. Use these when it misbehaves; switch them back when it is fixed.",
  handOver: {
    label: "Pass every customer to the team",
    hint: "The assistant stops answering by itself: each new message waits for your team in the inbox (the customer hears that a colleague will reply), and calls go to your forwarding number.",
  },
  actions: {
    title: "What the assistant may do",
    hint: "An action switched off is refused when the assistant tries it; it then takes a request or passes the customer to a colleague.",
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
