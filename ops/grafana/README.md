# Grafana dashboards

`workshop-service.json` graphs the Prometheus series of the API and the
worker (docs/operations/observability.md) and the service levels they
feed (docs/operations/slo.md). Import it in Grafana (Dashboards → New →
Import → upload the file) and pick the Prometheus data source that
scrapes `/metrics`; the dashboard asks for it through its `datasource`
variable, so one file serves every environment.

| Row | What it answers |
| --- | --- |
| Service levels | replies within 60 s, answer p95, API 5xx ratio, and the burn rates of both budgets per alert window (1 h & 5 min against 14.4, 6 h & 30 min against 6) |
| HTTP | requests by status class, the slowest routes at p95, rate-limit rejections |
| Webhooks and the job queue | messages received, queued and duplicate; pickup delay, due jobs and the oldest wait per lane; dead letters |
| Answers and language models | answer latency per channel; model latency, errors and tokens per provider and model |
| Outbound sends | attempts and failures per provider |
| Database pool and resilience | connections in use, waits for one, circuit breaker states, process memory |

The figures of record for the SLOs are the rows `record_sli` writes
(`service_level_slots`, `service_level_hours`): the error budget card on
`/admin/system` and the burn-rate alerts in `ops/alerts/` read those, not
Prometheus. The dashboard's service level row approximates them from the
histograms (stored replies only, handoffs not counted) to show the trend
between scrapes.

`tests/platform/test_grafana_dashboards.py` fails when a query names a
series the services no longer expose, filters on a histogram bucket that
does not exist, or a panel stops using the `datasource` variable. Edit the
dashboard in Grafana, export it with "Export for sharing externally" off,
and replace the file; keep the `datasource` variable.
