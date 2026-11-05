'use strict';

const crypto = require('node:crypto');

// `Workshop-Signature: t=<unix seconds>,v1=<hex>`: HMAC-SHA256 of
// `<t>.<raw body>` keyed with the endpoint's whole signing secret
// (`whsec_…`). See docs/api-versioning.md, "Webhook requests".

const TOLERANCE_SECONDS = 300;

function parseSignature(header) {
  const parts = {};
  for (const piece of String(header || '').split(',')) {
    const [name, value] = piece.split('=', 2);
    if (name && value) {
      parts[name.trim()] = value.trim();
    }
  }
  const timestamp = Number(parts.t);
  if (!Number.isInteger(timestamp) || !/^[0-9a-f]{64}$/.test(parts.v1 || '')) {
    return null;
  }
  return { timestamp, digest: parts.v1 };
}

function isValidSignature(secret, header, rawBody, nowSeconds) {
  const signature = parseSignature(header);
  if (!secret || signature === null) {
    return false;
  }
  if (Math.abs(nowSeconds - signature.timestamp) > TOLERANCE_SECONDS) {
    return false;
  }
  const expected = crypto
    .createHmac('sha256', secret)
    .update(`${signature.timestamp}.${rawBody}`)
    .digest();
  const given = Buffer.from(signature.digest, 'hex');
  return given.length === expected.length && crypto.timingSafeEqual(given, expected);
}

// Zapier passes a hook's headers as `Http-<Name>`; plain names are read too.
function readHeader(headers, name) {
  const wanted = [name.toLowerCase(), `http-${name.toLowerCase()}`];
  for (const [key, value] of Object.entries(headers || {})) {
    if (wanted.includes(key.toLowerCase())) {
      return value;
    }
  }
  return undefined;
}

module.exports = { TOLERANCE_SECONDS, isValidSignature, parseSignature, readHeader };
