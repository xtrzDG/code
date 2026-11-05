'use strict';

const { hookTrigger } = require('../lib/hooks');
const samples = require('../lib/samples');

// One REST-hook trigger per event type a Zap can start from.
const definitions = [
  ['new_booking', 'Booking', 'New Booking', 'Triggers when a booking is made (by the assistant, staff or the API).', 'booking.created', '/bookings', samples.booking],
  ['updated_booking', 'Booking', 'Updated Booking', 'Triggers when a booking is changed or moved.', 'booking.updated', '/bookings', samples.booking],
  ['cancelled_booking', 'Booking', 'Cancelled Booking', 'Triggers when a booking is cancelled.', 'booking.cancelled', null, { ...samples.booking, status: 'cancelled' }],
  ['new_lead', 'Lead', 'New Lead', 'Triggers when a request is passed to the team (a banquet, a group, an order...).', 'lead.created', '/leads', samples.lead],
  ['updated_lead', 'Lead', 'Updated Lead', 'Triggers when a lead changes state.', 'lead.updated', '/leads', samples.lead],
  ['new_handoff', 'Handoff', 'New Handoff', 'Triggers when the assistant passes a conversation to a person.', 'handoff.created', null, samples.handoff],
  ['resolved_handoff', 'Handoff', 'Resolved Handoff', 'Triggers when the team resolves a handoff.', 'handoff.resolved', null, { ...samples.handoff, status: 'resolved' }],
  ['new_conversation', 'Conversation', 'New Conversation', 'Triggers when a customer starts a conversation in any channel.', 'conversation.started', '/conversations', samples.conversation],
  ['finished_call', 'Call', 'Finished Call', 'Triggers when the assistant finishes a phone call, with its summary.', 'call.finished', null, samples.call],
];

module.exports = Object.fromEntries(
  definitions.map(([key, noun, label, description, eventType, listPath, sample]) => [
    key,
    hookTrigger({
      key,
      noun,
      label,
      description,
      eventType,
      listPath,
      sample: samples.withEvent(sample, eventType),
    }),
  ])
);
