'use strict';

const { apiUrl } = require('../lib/api');
const samples = require('../lib/samples');
const { contactFields, idempotencyHeaders, requestBody } = require('./fields');

// `POST /v1/public-api/leads` (scope `leads:write`): a request the team
// follows up, from a contact form or a CRM.

const KEYS = [
  'contact_name', 'contact_phone_number', 'type', 'details', 'requested_date',
  'party_size', 'budget', 'language',
];

module.exports = {
  key: 'create_lead',
  noun: 'Lead',
  display: {
    label: 'Create Lead',
    description: 'Passes a request (a banquet, a group, an order...) to the team.',
  },
  operation: {
    inputFields: [
      ...contactFields,
      {
        key: 'type',
        label: 'Kind',
        required: true,
        choices: {
          banquet: 'Banquet or event',
          group: 'Group',
          corporate: 'Corporate',
          order: 'Order',
          viewing: 'Viewing',
          other: 'Other',
        },
      },
      { key: 'details', label: 'Details', type: 'text', required: true },
      { key: 'requested_date', label: 'Date', helpText: 'YYYY-MM-DD, if the request has one.' },
      { key: 'party_size', label: 'Guests', type: 'integer' },
      { key: 'budget', label: 'Budget', helpText: 'In the customer\'s words, e.g. "about 4000 GEL".' },
    ],
    perform: async (z, bundle) => {
      const body = requestBody(bundle.inputData, KEYS);
      const response = await z.request({
        url: apiUrl('/leads'),
        method: 'POST',
        headers: idempotencyHeaders(bundle, 'lead', body),
        body,
      });
      return response.data;
    },
    sample: samples.lead,
  },
};
