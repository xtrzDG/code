'use strict';

const crypto = require('node:crypto');

// Input fields shared by the create actions: the customer, and dropping
// fields a Zap left empty (the API refuses unknown or empty values).

const contactFields = [
  { key: 'contact_name', label: 'Customer name', required: true },
  {
    key: 'contact_phone_number',
    label: 'Customer phone',
    helpText: 'In international form, e.g. +995 555 12 34 56. A customer with this phone is reused.',
  },
  {
    key: 'language',
    label: 'Language',
    helpText: 'The customer\'s language as a tag (ka, ru, en...), for messages to them.',
  },
];

const INTEGER_FIELDS = new Set(['party_size', 'duration_minutes', 'nights']);

function requestBody(inputData, keys) {
  const body = {};
  for (const key of keys) {
    const value = inputData[key];
    if (value === undefined || value === null || value === '') {
      continue;
    }
    body[key] = INTEGER_FIELDS.has(key) ? Number(value) : value;
  }
  return body;
}

// One key per Zap and input: a retried step replays the first answer.
function idempotencyHeaders(bundle, kind, body) {
  const zapId = bundle.meta && bundle.meta.zap && bundle.meta.zap.id;
  if (!zapId) {
    return {};
  }
  const digest = crypto
    .createHash('sha256')
    .update(JSON.stringify([kind, String(zapId), body]))
    .digest('hex');
  return { 'Idempotency-Key': `zapier-${digest.slice(0, 40)}` };
}

module.exports = { contactFields, idempotencyHeaders, requestBody };
