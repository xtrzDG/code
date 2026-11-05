'use strict';

const assert = require('node:assert/strict');
const { beforeEach, test } = require('node:test');
const app = require('../index');
const { explainErrors, includeApiKey } = require('../lib/api');
const { API_URL, fakeResponse, fakeZapier } = require('./fake_zapier');

const API_KEY = `awk_aaaaaaaa_${'0'.repeat(40)}`;

beforeEach(() => {
  process.env.WORKSHOP_API_URL = API_URL;
});

test('a booking is created with the filled fields only, numbers as numbers', async () => {
  const z = fakeZapier([{ id: 'booking_1' }]);
  const bundle = {
    inputData: { contact_name: 'Nino', date: '2026-10-09', time: '19:00', party_size: '4', notes: '' },
    meta: { zap: { id: 7 } },
  };
  const booking = await app.creates.create_booking.operation.perform(z, bundle);
  assert.equal(booking.id, 'booking_1');
  assert.equal(z.requests[0].url, `${API_URL}/v1/public-api/bookings`);
  assert.deepEqual(z.requests[0].body, { contact_name: 'Nino', date: '2026-10-09', time: '19:00', party_size: 4 });
  assert.match(z.requests[0].headers['Idempotency-Key'], /^zapier-[0-9a-f]{40}$/);
});

test('the same input from the same Zap is the same Idempotency-Key', async () => {
  const z = fakeZapier([{}, {}, {}]);
  const input = { contact_name: 'Nino', type: 'banquet', details: 'A banquet for 40' };
  const perform = app.creates.create_lead.operation.perform;
  await perform(z, { inputData: input, meta: { zap: { id: 7 } } });
  await perform(z, { inputData: input, meta: { zap: { id: 7 } } });
  await perform(z, { inputData: input, meta: { zap: { id: 8 } } });
  const keys = z.requests.map((request) => request.headers['Idempotency-Key']);
  assert.equal(keys[0], keys[1]);
  assert.notEqual(keys[0], keys[2]);
  assert.equal(z.requests[0].url, `${API_URL}/v1/public-api/leads`);
});

test('the key goes on every request as a bearer token', () => {
  const request = includeApiKey({ url: 'x' }, fakeZapier(), { authData: { api_key: API_KEY } });
  assert.equal(request.headers.Authorization, `Bearer ${API_KEY}`);
});

test('the connection is tested against /me', async () => {
  const z = fakeZapier([{ business_name: 'Cafe', api_key_name: 'Zapier' }]);
  const identity = await app.authentication.test(z, {});
  assert.equal(identity.business_name, 'Cafe');
  assert.equal(z.requests[0].url, `${API_URL}/v1/public-api/me`);
});

test('errors are explained: a refused key asks to reconnect, a limit waits', () => {
  const z = fakeZapier();
  assert.throws(() => explainErrors(fakeResponse(401, { message: 'The API key is not valid.' }), z), z.errors.RefreshAuthError);
  assert.throws(
    () => explainErrors(fakeResponse(429, { message: 'Slow down.' }, { 'retry-after': '30' }), z),
    (error) => error instanceof z.errors.ThrottledError && error.delay === 30
  );
  assert.throws(
    () => explainErrors(fakeResponse(403, { error: 'forbidden', message: 'The key lacks a scope.' }), z),
    (error) => error.code === 'forbidden' && error.status === 403
  );
  const ok = fakeResponse(200, {});
  assert.equal(explainErrors(ok, z), ok);
});

test('the API address must be https', async () => {
  process.env.WORKSHOP_API_URL = 'http://api.example.test';
  await assert.rejects(app.authentication.test(fakeZapier(), {}), /WORKSHOP_API_URL/);
});
