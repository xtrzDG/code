'use strict';

// Example records for the Zap editor, shaped as the public API returns
// them (docs/api-versioning.md). The identifiers are made up.

const contact = {
  id: 'contact_00000000-0000-4000-8000-000000000001',
  name: 'Nino Beridze',
  phone_number: '+995555000001',
};

const booking = {
  id: 'booking_00000000-0000-4000-8000-000000000002',
  status: 'confirmed',
  starts_at: '2026-10-09T19:00:00+04:00',
  ends_at: '2026-10-09T21:00:00+04:00',
  timezone: 'Asia/Tbilisi',
  party_size: 4,
  resource: { id: 'resource_00000000-0000-4000-8000-000000000003', name: 'Terrace table' },
  service: null,
  value: { amount_minor: 24000, currency: 'GEL' },
  notes: 'Window seat, a birthday',
  contact,
  source_channel: 'whatsapp',
  acquisition_source: 'instagram-bio',
  conversation_id: 'conversation_00000000-0000-4000-8000-000000000004',
  created_at: '2026-10-06T12:30:00+04:00',
  updated_at: '2026-10-06T12:30:00+04:00',
};

const lead = {
  id: 'lead_00000000-0000-4000-8000-000000000005',
  status: 'new',
  type: 'banquet',
  details: 'A banquet for 40 guests with a set menu',
  requested_date: '2026-11-14',
  party_size: 40,
  budget: 'about 4000 GEL',
  contact,
  source_channel: 'telegram',
  acquisition_source: null,
  conversation_id: 'conversation_00000000-0000-4000-8000-000000000004',
  created_at: '2026-10-06T12:30:00+04:00',
  updated_at: '2026-10-06T12:30:00+04:00',
};

const handoff = {
  id: 'handoff_00000000-0000-4000-8000-000000000006',
  status: 'notified',
  reason: 'customer_request',
  urgency: 'normal',
  summary: 'The guest asks to speak to the manager about a refund.',
  conversation_id: 'conversation_00000000-0000-4000-8000-000000000004',
  contact,
  created_at: '2026-10-06T12:30:00+04:00',
  resolved_at: null,
};

const conversation = {
  id: 'conversation_00000000-0000-4000-8000-000000000004',
  channel: 'whatsapp',
  status: 'open',
  contact,
  language: 'ka',
  acquisition_source: 'instagram-bio',
  summary: null,
  started_at: '2026-10-06T12:28:00+04:00',
  last_message_at: '2026-10-06T12:30:00+04:00',
};

const call = {
  id: 'call_00000000-0000-4000-8000-000000000007',
  conversation_id: 'conversation_00000000-0000-4000-8000-000000000004',
  from_phone_number: '+995555000001',
  to_phone_number: '+995322000000',
  started_at: '2026-10-06T12:20:00+04:00',
  duration_seconds: 94,
  outcome: 'booking',
  summary: 'Booked a table for four on Friday at 19:00.',
  contact,
  acquisition_source: null,
};

function withEvent(record, type) {
  return {
    ...record,
    event_id: 'event_00000000-0000-4000-8000-000000000008',
    event_type: type,
    event_created_at: '2026-10-06T12:30:00+04:00',
  };
}

module.exports = { booking, call, contact, conversation, handoff, lead, withEvent };
