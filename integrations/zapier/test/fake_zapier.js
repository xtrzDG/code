'use strict';

const crypto = require('node:crypto');

// A stand-in for Zapier's `z` (no network): requests are recorded and
// answered from a queue.

class ZapierError extends Error {
  constructor(message, code, status) {
    super(message);
    this.code = code;
    this.status = status;
  }
}
class RefreshAuthError extends Error {}
class ThrottledError extends Error {
  constructor(message, delay) {
    super(message);
    this.delay = delay;
  }
}

function fakeZapier(answers = []) {
  const requests = [];
  const queue = [...answers];
  return {
    requests,
    errors: { Error: ZapierError, RefreshAuthError, ThrottledError },
    request: async (options) => {
      requests.push(options);
      return { status: 200, data: queue.length ? queue.shift() : {} };
    },
  };
}

function fakeResponse(status, data, headers = {}) {
  return {
    status,
    data,
    content: JSON.stringify(data),
    getHeader: (name) => headers[name.toLowerCase()],
  };
}

const API_URL = 'https://api.example.test';
const SECRET = `whsec_${'0'.repeat(43)}`;

// A `Workshop-Signature` header as the API makes it.
function sign(secret, timestamp, body) {
  const digest = crypto.createHmac('sha256', secret).update(`${timestamp}.${body}`).digest('hex');
  return `t=${timestamp},v1=${digest}`;
}

module.exports = { API_URL, SECRET, fakeResponse, fakeZapier, sign };
