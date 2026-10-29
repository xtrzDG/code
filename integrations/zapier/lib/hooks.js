'use strict';

const { apiUrl } = require('./api');
const { isValidSignature, readHeader } = require('./signature');

// A REST-hook trigger: turning a Zap on subscribes Zapier's URL to one
// event type (`POST /v1/public-api/webhooks`, the key needs
// `webhooks:manage`), turning it off unsubscribes it. Every request is
// checked against the signing secret the subscription answered.

async function subscribe(z, bundle, eventType) {
  const response = await z.request({
    url: apiUrl('/webhooks'),
    method: 'POST',
    body: {
      url: bundle.targetUrl,
      event_types: [eventType],
      label: `Zapier: ${eventType}`,
    },
  });
  const created = response.data;
  return { id: created.endpoint.id, signing_secret: created.signing_secret };
}

async function unsubscribe(z, bundle) {
  const subscription = bundle.subscribeData || {};
  if (!subscription.id) {
    return {};
  }
  await z.request({
    url: apiUrl(`/webhooks/${encodeURIComponent(subscription.id)}`),
    method: 'DELETE',
  });
  return {};
}

// Fails closed: an event without a signature that checks out against the
// subscription's secret (no secret, no raw body, a wrong or stale
// signature) is refused, never passed on unchecked.
function receive(z, bundle, nowSeconds = Math.floor(Date.now() / 1000)) {
  const secret = (bundle.subscribeData || {}).signing_secret;
  if (!secret) {
    throw new z.errors.Error(
      'This subscription has no signing secret; turn the Zap off and on again.',
      'missing_secret',
      401
    );
  }
  const raw = bundle.rawRequest || {};
  const content = typeof raw.content === 'string' ? raw.content : null;
  const header = readHeader(raw.headers, 'Workshop-Signature');
  if (content === null || !isValidSignature(secret, header, content, nowSeconds)) {
    throw new z.errors.Error('The webhook signature is not valid.', 'bad_signature', 401);
  }
  const event = bundle.cleanedRequest || {};
  if (!event.data) {
    return [];
  }
  return [describe(event.data, event)];
}

// The record with the event that announced it; a record's `id` stays
// itself (Zapier does not deduplicate hooks), `event_id` tells repeats.
function describe(record, event) {
  return {
    ...record,
    event_id: event.id,
    event_type: event.type,
    event_created_at: event.created_at,
  };
}

function hookTrigger({ key, noun, label, description, eventType, listPath, sample }) {
  const operation = {
    type: 'hook',
    performSubscribe: (z, bundle) => subscribe(z, bundle, eventType),
    performUnsubscribe: (z, bundle) => unsubscribe(z, bundle),
    perform: (z, bundle) => receive(z, bundle),
    sample,
  };
  if (listPath) {
    // Recent records for the Zap editor's test step (the read scope of
    // the records is needed for it).
    operation.performList = async (z) => {
      const response = await z.request({ url: apiUrl(listPath), params: { limit: 3 } });
      return response.data.items.map((record) =>
        describe(record, { id: null, type: eventType, created_at: record.created_at })
      );
    };
  }
  return { key, noun, display: { label, description }, operation };
}

module.exports = { describe, hookTrigger, receive, subscribe, unsubscribe };
