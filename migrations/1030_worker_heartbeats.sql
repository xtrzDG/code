-- 1030_worker_heartbeats
--
-- The pulse of every background worker process. A worker writes its row on
-- every tick of its periodic thread (build, start, last periodic results);
-- GET /readyz of the API reports how old the freshest one is, so a stopped
-- or stuck worker shows up before customers notice unanswered messages.
-- A worker deletes rows older than a day when it starts (one row per
-- process: restarts and deploys leave old ones behind).
--
-- A platform collection (no business, no tenant rows).

select workshop.create_document_collection('worker_heartbeats');

alter table workshop.worker_heartbeats
    add column if not exists doc_beat_at bigint
        generated always as ((document ->> 'beat_at')::bigint) stored;
create index if not exists worker_heartbeats_doc_beat_at_idx
    on workshop.worker_heartbeats (doc_beat_at);
