# Database or object storage errors

**Alert:** `storage_errors` (SEV1): more than 5 requests or jobs failed in
15 to 30 minutes because the database (a Postgres error underneath) or the
object storage (recordings, files, export archives) failed. The processes
that answered the request or ran the job count it. A database that is down
altogether also stops this count: `GET /readyz` (the uptime monitor) and
`worker_down` cover that ([database-failover](database-failover.md)).

## Check

1. The message says how many failures were the database's and how many the
   object storage's.
2. Database: Render's Postgres dashboard (connections, CPU, disk, recent
   restarts), the worker and API logs (`ExternalServiceError` with the
   collection), `GET /readyz` (pool saturation). Connection slots used up
   point to [stuck-worker](stuck-worker.md) or a pool too small.
3. Object storage: the provider's status page, the bucket's credentials
   (`RECORDINGS_S3_*`), the errors' HTTP status in the logs (403: keys or
   policy; 5xx: the provider).

## Mitigate and fix

- Database restarting or failing over: [database-failover](database-failover.md).
- Disk full or slow queries: raise the plan or end the long query; check
  the data tasks on Admin → System.
- Object storage: fix the credentials or wait for the provider; recordings
  and files queued for upload retry.

## Afterwards

The alert resolves when a window counts 5 or fewer failures. Look for jobs
that ran out of attempts meanwhile (`dead_jobs`) and retry them.
