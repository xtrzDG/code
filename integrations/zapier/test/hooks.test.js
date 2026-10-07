'use strict';

const assert = require('node:assert/strict');
const { beforeEach, test } = require('node:test');
const app = require('../index');
const { receive } = require('../lib/hooks');
const { API_URL, SECRET, fakeZapier, sign } = require('./fake_zapier');

const NOW = 1791331200;
const EVENT = {
  id: 'event_1',
  type: 'booking.created',
  created_at: '2026-10-06T12:30:00+04:00',
  business_id: 'business_1',
  data: { id: 'booking_1', status: 'confirmed' },
};

beforeEach(() => {
  process.env.WORKSHOP_API_URL = `${API_URL}/`;
});

test('turning a Zap on subscribes the hook URL to one event type', async () => {
  const z = fakeZapier([{ endpoint: { id: 'webhook_1' }, signing_secret: SECRET }]);
  const operation = app.triggers.new_booking.operation;
  const subscription = await operation.performSubscribe(z, { targetUrl: 'https://hooks.zapier.com/1' });
  assert.deepEqual(subscription, { id: 'webhook_1', signing_secret: SECRET });
  assert.equal(z.requests[0].url, `${API_URL}/v1/public-api/webhooks`);
  assert.equal(z.requests[0].method, 'POST');
  assert.deepEqual(z.requests[0].body.event_types, ['booking.created']);
  assert.equal(z.requests[0].body.url, 'https://hooks.zapier.com/1');
});

test('turning it off unsubscribes, and nothing is sent without a subscription', async () => {
  const z = fakeZapier();
  const operation = app.triggers.new_lead.operation;
  await operation.performUnsubscribe(z, { subscribeData: { id: 'webhook_1' } });
  await operation.performUnsubscribe(z, {});
  assert.equal(z.requests.length, 1);
  assert.equal(z.requests[0].method, 'DELETE');
  assert.equal(z.requests[0].url, `${API_URL}/v1/public-api/webhooks/webhook_1`);
});

test('a signed event becomes the record with its event', () => {
  const content = JSON.stringify(EVENT);
  const bundle = {
    subscribeData: { id: 'webhook_1', signing_secret: SECRET },
    rawRequest: { headers: { 'Http-Workshop-Signature': sign(SECRET, NOW, content) }, content },
    cleanedRequest: EVENT,
  };
  const [record] = receive(fakeZapier(), bundle, NOW);
  assert.equal(record.id, 'booking_1');
  assert.equal(record.event_id, 'event_1');
  assert.equal(record.event_type, 'booking.created');
});

test('an event with a wrong signature is refused', () => {
  const content = JSON.stringify(EVENT);
  const bundle = {
    subscribeData: { signing_secret: SECRET },
    rawRequest: { headers: { 'Http-Workshop-Signature': sign(SECRET, NOW, '{}') }, content },
    cleanedRequest: EVENT,
  };
  assert.throws(() => receive(fakeZapier(), bundle, NOW), /signature is not valid/);
});

test('an event that cannot be checked is refused, never passed on', () => {
  const content = JSON.stringify(EVENT);
  const signed = { 'Http-Workshop-Signature': sign(SECRET, NOW, content) };
  const unchecked = [
    { subscribeData: {}, rawRequest: { headers: signed, content }, cleanedRequest: EVENT },
    { subscribeData: { signing_secret: SECRET }, cleanedRequest: EVENT },
    { subscribeData: { signing_secret: SECRET }, rawRequest: { headers: signed }, cleanedRequest: EVENT },
    { subscribeData: { signing_secret: SECRET }, rawRequest: { headers: {}, content }, cleanedRequest: EVENT },
  ];
  for (const bundle of unchecked) {
    assert.throws(() => receive(fakeZapier(), bundle, NOW), /signing secret|signature is not valid/);
  }
});

test('a replayed event older than five minutes is refused', () => {
  const content = JSON.stringify(EVENT);
  const bundle = {
    subscribeData: { signing_secret: SECRET },
    rawRequest: { headers: { 'Http-Workshop-Signature': sign(SECRET, NOW, content) }, content },
    cleanedRequest: EVENT,
  };
  assert.throws(() => receive(fakeZapier(), bundle, NOW + 301), /signature is not valid/);
});

test('the editor\'s test step lists recent records', async () => {
  const z = fakeZapier([{ items: [{ id: 'booking_2', created_at: '2026-10-06T10:00:00+04:00' }] }]);
  const records = await app.triggers.new_booking.operation.performList(z, {});
  assert.equal(z.requests[0].url, `${API_URL}/v1/public-api/bookings`);
  assert.equal(records[0].id, 'booking_2');
  assert.equal(records[0].event_type, 'booking.created');
});

test('every trigger is a REST hook with a sample', () => {
  for (const [key, trigger] of Object.entries(app.triggers)) {
    assert.equal(trigger.key, key);
    assert.equal(trigger.operation.type, 'hook');
    assert.equal(typeof trigger.operation.perform, 'function');
    assert.ok(trigger.operation.sample.id, key);
  }
});
