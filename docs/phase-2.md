# Phase 2 scope

## Included

- PostgreSQL data model: `customers`, `products`, `orders`, `order_items` via SQLAlchemy ORM models
- Alembic migrations tracking the PostgreSQL schema
- MongoDB collections for the same domain: `customers`, `products`, `orders` (order line items embedded directly in the order document)
- Seeded sample-data generation shared across both stores (`POST /api/dataset/generate`)
- Dataset reset (`POST /api/dataset/reset`) and status (`GET /api/dataset/status`) endpoints
- Backend unit tests for the generation logic and the dataset API

## Deliberately deferred

Query consoles, browsing/editing individual rows or documents, schema diagrams, side-by-side structure-comparison lessons, transactions, and indexes remain in later phases.

## Why the two stores are modeled differently

The same logical data (customers, products, orders) is generated into both databases from one seeded source, but shaped the way each database naturally encourages, so the contrast itself is the teaching point:

- **PostgreSQL** normalizes: an order references its customer by foreign key, and its line items live in a separate `order_items` table joined back to `orders` and `products`. Seeing the contents of one order takes a join.
- **MongoDB** embeds: each order document carries its `items` array directly, with a `product_name` snapshot alongside the `product_id` reference. Reading one order is a single document fetch, at the cost of that snapshot going stale if the product is later renamed -- a concrete example of the denormalization trade-off.

## Schema changes

The PostgreSQL schema is tracked with Alembic (`backend/alembic/`). A fresh, empty database also gets bootstrapped automatically the first time any `/api/dataset/*` endpoint runs (`Base.metadata.create_all`), so a brand new Docker volume or desktop-app data directory doesn't require a manual migration step. Alembic is what matters once a database already has data: any future schema change must ship as a new revision (`alembic revision --autogenerate -m "..."`) so existing installs can upgrade in place instead of losing data to a recreated table.
