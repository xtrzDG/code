-- 1211_knowledge_embeddings
--
-- Vectors of the knowledge items for the hybrid knowledge search
-- (R17-CROSS-LANG-SEARCH): a question in Georgian finds an item titled in
-- English by meaning, next to the lexical match of titles and aliases.
--
--   workshop.knowledge_embeddings
--   business_id  text not null     owning business (row-level security of
--                                   the tenant and platform roles, 1200)
--   item_id      text not null     the knowledge item (a brand's shared item
--                                   merged into a location keeps its id)
--   model_id     text not null     the embedding model: vectors of different
--                                   models are never compared
--   fingerprint  text not null     SHA-256 of the model and the text the
--                                   vector was computed from (stale when the
--                                   item's text changed)
--   embedding    vector not null   pgvector, of the model's dimension
--   updated_at   bigint not null   last write, UNIX microseconds
--   primary key (business_id, item_id)
--
-- No approximate index: one search reads one business's rows (tens to a
-- few hundred) by the primary key's prefix and ranks them exactly, which
-- an HNSW index filtered by business would only make slower and inexact.
--
-- Guarded by the extension's availability. pgvector is an extension of the
-- server: `workshop.enable_knowledge_embeddings()` creates it when the
-- server offers it and this role may create it, then the table. Without it
-- the function changes nothing and returns false; the application sees no
-- table and keeps the search lexical (EMBEDDINGS_API_KEY then has no
-- effect). Once an administrator installed the extension
-- (`create extension vector;` as a superuser), run the function again:
--
--   select workshop.enable_knowledge_embeddings();
--
-- It is idempotent. The table is new and empty, so nothing in it blocks
-- the live release.

create or replace function workshop.enable_knowledge_embeddings()
returns boolean
language plpgsql
set search_path = pg_catalog
as $function$
declare
    vector_schema text;
begin
    select n.nspname into vector_schema
      from pg_catalog.pg_extension e
      join pg_catalog.pg_namespace n on n.oid = e.extnamespace
     where e.extname = 'vector';

    if vector_schema is null then
        if not exists (
            select from pg_catalog.pg_available_extensions where name = 'vector'
        ) then
            raise notice 'pgvector is not available on this server: the knowledge search stays lexical.';
            return false;
        end if;

        begin
            create extension if not exists vector with schema public;
        exception when insufficient_privilege then
            raise notice 'pgvector is available, but this role may not create it: as an administrator run "create extension vector;", then "select workshop.enable_knowledge_embeddings();".';
            return false;
        end;

        select n.nspname into vector_schema
          from pg_catalog.pg_extension e
          join pg_catalog.pg_namespace n on n.oid = e.extnamespace
         where e.extname = 'vector';
    end if;

    execute format(
        'create table if not exists workshop.knowledge_embeddings ('
        '    business_id text not null,'
        '    item_id text not null,'
        '    model_id text not null,'
        '    fingerprint text not null,'
        '    embedding %I.vector not null,'
        '    updated_at bigint not null,'
        '    primary key (business_id, item_id)'
        ')',
        vector_schema
    );
    execute 'alter table workshop.knowledge_embeddings enable row level security';
    execute 'alter table workshop.knowledge_embeddings force row level security';
    -- The tenant role's rows of its business and the platform role's every
    -- row (1200); no policy reads app.bypass_rls. The grants are explicit:
    -- the default privileges of 1200 cover only tables the migration role
    -- creates, and an administrator may be the one who runs this.
    perform workshop.apply_role_policies('workshop.knowledge_embeddings'::regclass);
    execute 'grant select, insert, update, delete on workshop.knowledge_embeddings'
        ' to workshop_tenant, workshop_platform';

    return true;
end;
$function$;

comment on function workshop.enable_knowledge_embeddings() is
    'Create pgvector (where the server offers it) and the knowledge embeddings table; false without pgvector (1211).';

revoke all on function workshop.enable_knowledge_embeddings() from public;

select workshop.enable_knowledge_embeddings();
