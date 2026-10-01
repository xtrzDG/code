#!/bin/sh
# First start of the local Postgres container (docker-compose.yml): create
# the application role and its database. The role is neither superuser nor
# BYPASSRLS, so the row-level security of the migrations binds it; it owns
# the database and runs the migrations.
set -eu

psql --variable=ON_ERROR_STOP=1 \
  --username "$POSTGRES_USER" --dbname "$POSTGRES_DB" \
  --set=app_role="${WORKSHOP_DB_USER:-workshop}" \
  --set=app_password="${WORKSHOP_DB_PASSWORD:-workshop}" \
  --set=app_database="${WORKSHOP_DB_NAME:-workshop}" <<'SQL'
create role :"app_role" login password :'app_password'
  nosuperuser nobypassrls nocreatedb nocreaterole;
create database :"app_database" owner :"app_role";
SQL
