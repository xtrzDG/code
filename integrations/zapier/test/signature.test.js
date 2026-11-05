'use strict';

const assert = require('node:assert/strict');
const { test } = require('node:test');
const { isValidSignature, parseSignature, readHeader } = require('../lib/signature');
const { SECRET, sign } = require('./fake_zapier');

const BODY = '{"id":"event_1","type":"booking.created","data":{}}';
const NOW = 1791331200;

test('a signature made with the secret over the raw body is valid', () => {
  assert.equal(isValidSignature(SECRET, sign(SECRET, NOW, BODY), BODY, NOW + 10), true);
});

test('another secret, another body or an old timestamp is refused', () => {
  const other = `whsec_${'1'.repeat(43)}`;
  assert.equal(isValidSignature(SECRET, sign(other, NOW, BODY), BODY, NOW), false);
  assert.equal(isValidSignature(SECRET, sign(SECRET, NOW, BODY), `${BODY} `, NOW), false);
  assert.equal(isValidSignature(SECRET, sign(SECRET, NOW, BODY), BODY, NOW + 301), false);
});

test('a malformed header is refused', () => {
  assert.equal(parseSignature('t=abc,v1=00'), null);
  assert.equal(parseSignature(undefined), null);
  assert.equal(isValidSignature(SECRET, 'v1=zz', BODY, NOW), false);
  assert.equal(isValidSignature('', sign(SECRET, NOW, BODY), BODY, NOW), false);
});

test('headers are read as Zapier passes them', () => {
  assert.equal(readHeader({ 'Http-Workshop-Signature': 'x' }, 'Workshop-Signature'), 'x');
  assert.equal(readHeader({ 'workshop-signature': 'y' }, 'Workshop-Signature'), 'y');
  assert.equal(readHeader({}, 'Workshop-Signature'), undefined);
});
