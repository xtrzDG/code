# API latency

**Alert:** `api_latency` (SEV2): more than 5 % of the API requests of the
last 30 minutes took longer than 2 s (at least 200 requests; health probes
do not count). The website chat and the cabinet feel slow; the status page
shows them degraded while it fires.

## Check

1. Grafana (`ops/grafana`): the request duration by route template. One
   route slow, or all of them?
2. `GET /readyz`: the pool's saturation and the request threads. All
   threads busy point to slow calls inside requests (a provider, the
   database).
3. Render: the API's CPU and memory, and whether a deploy just started.
4. The database: slow queries, locks, a data task running
   ([storage-errors](storage-errors.md)).

## Mitigate and fix

- One slow provider inside requests: its circuit opens after repeated
  failures ([provider-circuits](provider-circuits.md)); lower its timeout
  or take the call out of the request.
- Saturated instance: scale the API out (Render instance count) or up.
- A bad deploy: roll back ([bad-deploy](bad-deploy.md)).

## Afterwards

The alert resolves when the share of slow requests is 5 % or less. Record
the cause and, for a lasting regression, the route's latency budget in
`tests/perf`.
