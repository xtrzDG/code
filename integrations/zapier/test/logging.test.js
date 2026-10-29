'use strict';

const assert = require('node:assert/strict');
const { test } = require('node:test');
const app = require('../index');
const authentication = require('../authentication');
const { API_URL, SECRET, fakeZapier } = require('./fake_zapier');

// Zapier's logs (HTTP requests and answers, bundles) censor every value
// whose key contains a sensitive word (@zapier/secret-scrubber, for example
// "api_key" and "secret") and the password fields of the authentication.
// The app's two secrets must stay under such keys, or they would be logged.
const CENSORED_WORDS = ['api_key', 'secret'];

function isCensoredKey(key) {
  return CENSORED_WORDS.some((word) => key.toLowerCase().includes(word));
}

test('the API key is a password field under a censored key', () => {
  const field = authentication.fields.find((candidate) => candidate.key === 'api_key');
  assert.ok(field);
  assert.equal(field.type, 'password');
  assert.ok(isCensoredKey(field.key));
});

test("a subscription's signing secret is kept under a censored key", async () => {
  process.env.WORKSHOP_API_URL = API_URL;
  const z = fakeZapier([{ endpoint: { id: 'webhook_1' }, signing_secret: SECRET }]);
  const subscription = await app.triggers.new_lead.operation.performSubscribe(z, {
    targetUrl: 'https://hooks.zapier.com/1',
  });
  const keysOfTheSecret = Object.entries(subscription)
    .filter(([, value]) => value === SECRET)
    .map(([key]) => key);
  assert.deepEqual(keysOfTheSecret, ['signing_secret']);
  assert.ok(keysOfTheSecret.every(isCensoredKey));
});
