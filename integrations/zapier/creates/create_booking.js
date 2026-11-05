'use strict';

const { apiUrl } = require('../lib/api');
const samples = require('../lib/samples');
const { contactFields, idempotencyHeaders, requestBody } = require('./fields');

// `POST /v1/public-api/bookings` (scope `bookings:write`): a booking as
// staff add one in the cabinet; capacity and opening hours are enforced.
// The same input from the same Zap is one Idempotency-Key, so a step that
// Zapier retries does not book twice.

const KEYS = [
  'contact_name', 'contact_phone_number', 'resource_id', 'service_id', 'date', 'time',
  'duration_minutes', 'nights', 'party_size', 'notes', 'language',
];

module.exports = {
  key: 'create_booking',
  noun: 'Booking',
  display: {
    label: 'Create Booking',
    description: 'Books a table, a visit, a service or a stay in the business\'s calendar.',
  },
  operation: {
    inputFields: [
      ...contactFields,
      { key: 'date', label: 'Date', required: true, helpText: 'YYYY-MM-DD, in the business\'s time zone.' },
      { key: 'time', label: 'Time', helpText: 'HH:MM, in the business\'s time zone (not for stays).' },
      { key: 'party_size', label: 'Guests', type: 'integer', required: true },
      { key: 'resource_id', label: 'Resource ID', helpText: 'A table, room or specialist (resource_…).' },
      { key: 'service_id', label: 'Service ID', helpText: 'A service, package or room type.' },
      { key: 'duration_minutes', label: 'Duration (minutes)', type: 'integer' },
      { key: 'nights', label: 'Nights', type: 'integer', helpText: 'For stays.' },
      { key: 'notes', label: 'Notes', type: 'text' },
    ],
    perform: async (z, bundle) => {
      const body = requestBody(bundle.inputData, KEYS);
      const response = await z.request({
        url: apiUrl('/bookings'),
        method: 'POST',
        headers: idempotencyHeaders(bundle, 'booking', body),
        body,
      });
      return response.data;
    },
    sample: samples.booking,
  },
};
