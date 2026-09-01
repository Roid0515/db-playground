#!/bin/sh
# Runs during the postgres image's own first-boot bootstrap, authenticated as
# POSTGRES_USER (the image's bootstrap superuser -- "postgres" by default,
# since docker-compose.yml deliberately doesn't override it). Creates a second,
# unprivileged role that the application actually connects as, so a SQL console
# bug or a learner's own query can never reach server-wide state: no CREATE
# ROLE, no ALTER SYSTEM, no reading arbitrary server-side files.
set -eu

psql -v ON_ERROR_STOP=1 --username "$POSTGRES_USER" --dbname "$POSTGRES_DB" <<-EOSQL
    DO \$\$
    BEGIN
        IF NOT EXISTS (SELECT FROM pg_catalog.pg_roles WHERE rolname = '${APP_DB_USER}') THEN
            CREATE ROLE "${APP_DB_USER}" WITH LOGIN PASSWORD '${APP_DB_PASSWORD}'
                NOSUPERUSER NOCREATEDB NOCREATEROLE NOREPLICATION;
        ELSE
            ALTER ROLE "${APP_DB_USER}" WITH LOGIN PASSWORD '${APP_DB_PASSWORD}'
                NOSUPERUSER NOCREATEDB NOCREATEROLE NOREPLICATION;
        END IF;
    END
    \$\$;

    GRANT ALL PRIVILEGES ON DATABASE "${POSTGRES_DB}" TO "${APP_DB_USER}";
    GRANT ALL ON SCHEMA public TO "${APP_DB_USER}";
    ALTER DEFAULT PRIVILEGES IN SCHEMA public GRANT ALL ON TABLES TO "${APP_DB_USER}";
    ALTER DEFAULT PRIVILEGES IN SCHEMA public GRANT ALL ON SEQUENCES TO "${APP_DB_USER}";
EOSQL
