# Phase 4 scope

## Included

- `GET /api/mongodb/collections`: lists real collections with document counts and a lightweight schema hint (one sample document's top-level field names)
- `GET /api/mongodb/collections/{name}/documents`: paginated document browsing
- `POST /api/mongodb/query`: runs one learner-submitted command in a safe mongosh-like syntax
- A "MongoDB" page mirroring Phase 3's relational page: a collection list, a document browser rendering each document as formatted JSON (not a flat table -- MongoDB's schema-flexible, embedded-document model is the whole teaching point, and forcing it into fixed table columns would hide that), and a console with runnable examples
- Backend and frontend tests for the above, including the command-safety validation

## Deliberately deferred

Structure comparison, transactions, and indexes remain in later phases.

## Mongo console safety model

Mirrors Phase 3's SQL console philosophy, adapted for MongoDB: real mongosh has no simple "single statement" or "DDL keyword" boundary the way SQL does, so `app/services/mongo_console.py` takes a narrower, allowlist-based approach instead of trying to parse general JavaScript:

- **A constrained syntax, not a JS interpreter.** Only `db.<collection>.<operation>(<args>)` is accepted, parsed by regex; arguments must be strict JSON (quoted keys included), not JS object literals or expressions. This is a real limitation -- no `$where` with a function body, no chained cursor methods -- but it keeps "what can actually run" fully enumerable, the same guarantee the SQL console makes.
- **An operation allowlist**, not a denylist: `find`, `aggregate`, `countDocuments`, `insertOne`, `insertMany`, `updateOne`, `updateMany`, `deleteOne`, `deleteMany`. Anything else (`drop`, `createIndex`, `renameCollection`, ...) is rejected outright -- this is the same "no schema/collection-admin operations" boundary the SQL console draws against DDL.
- **A query timeout and result cap**, via `maxTimeMS`/cursor `.limit()`, driven by the same settings Phase 3 introduced.
- **BSON-safe JSON serialization.** `ObjectId` and `datetime` values (which FastAPI can't serialize natively) are converted to plain strings via `app/services/bson_utils.to_jsonable` -- shared with Phase 5's comparison view, which returns the same kind of raw MongoDB documents.
- **The same database-level privilege boundary as Phase 3.** The app connects as a MongoDB user scoped to `readWrite`+`dbAdmin` on just the `db_playground` database, never a root role (see `docs/architecture.md`).

## Learning-flow decisions

- Documents are rendered as pretty-printed JSON cards, not table rows, in both the collection browser and query results -- deliberately different from Phase 3's `ResultsTable`, since a document's fields (and whether it has nested arrays/objects at all) can vary row to row.
- A write invalidates the same React Query keys as the collection browser and the dashboard's dataset panel, matching Phase 3's console.
