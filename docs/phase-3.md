# Phase 3 scope

## Included

- `GET /api/postgres/tables`: lists real tables (via SQLAlchemy `inspect()`, not a hardcoded list) with row counts and columns
- `GET /api/postgres/tables/{table}/rows`: paginated row browsing, ordered by primary key when one exists
- `POST /api/postgres/query`: runs one learner-submitted SQL statement -- SELECT, INSERT, UPDATE, or DELETE
- A "관계형 DB" page: a table list, a row browser, and a SQL console with runnable examples for each allowed statement type
- Backend and frontend tests for the above, including the SQL-safety validation

## Deliberately deferred

MongoDB browsing/querying, schema diagrams, comparison-lesson content, transactions, and indexes remain in later phases.

## SQL console safety model

This is a local, single-user learning sandbox, not a multi-tenant server -- the whole point of the console is letting the learner run their own SQL against their own practice data. What's actually enforced (`app/services/sql_console.py`) is narrower than "safe SQL" in general:

- **One statement at a time.** A `;`-separated second statement is rejected before anything runs, so a learner can't accidentally (or a stray copy-paste can't) smuggle in a second statement.
- **No DDL.** Only `SELECT`, `INSERT`, `UPDATE`, `DELETE` (and `WITH` ending in one of those) are allowed. `DROP`/`ALTER`/`CREATE`/`TRUNCATE` are rejected with a message pointing at Alembic -- the schema stays whatever the migration put there, no matter what a learner tries in the console.
- **A query timeout and a row cap**, both driven by the existing `QUERY_TIMEOUT_SECONDS` / `QUERY_MAX_ROWS` settings from Phase 1 (until now unused).
- **Raw execution, not templated.** The learner's SQL runs via `Connection.exec_driver_sql()`, not `session.execute(text(...))`. SQLAlchemy's `text()` scans the string for `:name`-style bind parameters, which misfires on legitimate SQL containing literal colons (time literals, JSON paths, `::` casts written with extra spacing); `exec_driver_sql` sends the string to the driver verbatim.
- **Errors are shown, not hidden.** Unlike the Phase 1 health checks (which deliberately hide driver errors), a failed query's actual database error is what tells the learner what went wrong, so it's surfaced -- lightly sanitized in case a `password=` substring ever ended up in a message.

## Learning-flow decisions

- Every write in the console invalidates the same React Query keys the table browser and the dashboard's dataset panel use, so an `INSERT`/`UPDATE`/`DELETE` is immediately visible everywhere without a manual refresh.
- The SQL editor is a plain `<textarea>`, not a syntax-highlighting editor (e.g. Monaco) -- reasonable for single-statement practice queries, and it keeps the frontend dependency footprint down. Revisit this only if a later phase's needs (e.g. multi-statement scripts, autocomplete) actually require it.
