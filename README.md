# Product Importer – Acme Inc

Backend coding assignment implementation for **Acme Inc – Product Importer**.

This is a FastAPI-based web application that:

- Uploads **large CSV files** (~500k products) and imports them into a **PostgreSQL** database.
- Uses **Celery + Redis** to run the import **asynchronously** (no web timeouts).
- Shows **real-time progress** of the upload/import in the UI using **Server-Sent Events (SSE)**.
- Provides a **Product Management UI** (filter, paginate, create, update, delete).
- Supports **bulk delete** from the UI with confirmation.
- Provides **Webhook configuration & testing** via UI and asynchronous workers.

---

## Table of Contents

- [Tech Stack](#tech-stack)
- [Architecture Overview](#architecture-overview)
- [Stories Coverage](#stories-coverage)
- [Local Setup (WSL / Linux / macOS)](#local-setup-wsl--linux--macos)
- [Running the App Locally](#running-the-app-locally)
- [CSV Format & Import Behaviour](#csv-format--import-behaviour)
- [Product Management UI](#product-management-ui)
- [Bulk Delete](#bulk-delete)
- [Webhooks](#webhooks)
- [Deployment Notes](#deployment-notes)
- [AI Assistance](#ai-assistance)

---

## Tech Stack

**Backend**

- Python, FastAPI
- SQLAlchemy (ORM)
- PostgreSQL
- Celery (asynchronous tasks)
- Redis (Celery broker + pub/sub for progress events)
- Alembic (database migrations)
- Gunicorn + UvicornWorker (production web server)

**Frontend**

- Plain HTML, CSS, and vanilla JavaScript  
- Single-page UI served from `app/static/index.html`

**Deployment**

- Designed to run on a PaaS like **Heroku** (web dyno + worker dyno).
- Uses environment variables for configuration (DB/Redis URLs, S3, etc.)

---

## Architecture Overview

**High-level components:**

- `app/main.py` – FastAPI app, routes, static UI.
- `app/models.py` – SQLAlchemy models (`Product`, `Webhook`).
- `app/schemas.py` – Pydantic schemas for request/response validation.
- `app/crud.py` – Database access helpers for products & webhooks.
- `app/tasks.py` – Celery tasks:
  - `import_csv` – heavy CSV import
  - `send_webhook` – async webhook POST
- `app/celery_app.py` – Celery application configuration.
- `app/static/index.html` – Single-page front-end:
  - File upload + progress bar
  - Product list + filter + pagination + edit/delete
  - Bulk delete dialog
  - Webhook management stub (if implemented)

**Import flow (large CSV):**

1. User uploads CSV via UI.
2. FastAPI endpoint saves or streams the file (local dev: disk; production: e.g. S3).
3. FastAPI enqueues a **Celery task** and immediately returns a `task_id`.
4. The worker:
   - Reads CSV in bulk using PostgreSQL `COPY` into a **temporary staging table**.
   - Deduplicates rows by **case-insensitive SKU** (keeps last occurrence).
   - Performs a single `INSERT .. ON CONFLICT (sku_lower) DO UPDATE` into `products`.
5. Progress events are pushed via Redis pub/sub.
6. The UI listens with SSE and updates the progress bar + status messages.

---

## Stories Coverage

### STORY 1 & 1A — File Upload + Progress

- File upload widget in UI (`index.html`).
- Backend endpoint `/api/upload`:
  - Accepts CSV file.
  - Enqueues Celery `import_csv` task.
- Real-time progress:
  - Worker periodically calls `publish(task_id, {...})`.
  - Frontend opens `/api/events?task_id=...` as an SSE stream.
  - UI renders:
    - statuses: “saved”, “creating_staging”, “copying”, “deduplicating”, “upserting”, “complete”, or “error”
    - progress bar width
- Timeouts solved:
  - Long-running import runs in Celery worker, not in web request.

**Deduplication and SKU semantics:**

- Database has a `sku_lower` generated/stored column with a **unique index**.
- Import uses `lower(sku)` for conflict detection, so `ABC123` and `abc123` are considered the same.
- On conflict:
  - existing row is **overwritten** with the latest data for that SKU.
- `active` is stored per product (default for imported products can be configured).

### STORY 2 — Product Management UI

- `/api/products` returns paginated list with filters.
- UI supports:
  - Filter by SKU, name, active status, (optionally description).
  - Paginated viewing with Next/Prev controls.
  - Edit product (name, description, price, active) via simple UI.
  - Delete single product with confirmation.
- Backend endpoints (FastAPI):
  - `GET /api/products`
  - `GET /api/products/{id}`
  - `POST /api/products`
  - `PUT /api/products/{id}`
  - `DELETE /api/products/{id}`

### STORY 3 — Bulk Delete

- UI has a **Delete All** button.
- Clicking opens a confirmation dialog:
  - “This will permanently delete all products. This action cannot be undone.”
- Backend endpoint:
  - `POST /api/products/bulk-delete?confirm=true`
  - Uses a `TRUNCATE TABLE products RESTART IDENTITY` for performance.
- UI shows status while deleting and refreshes the list after success.

### STORY 4 — Webhook Configuration

- Database model `Webhook`:
  - `name`, `url`, `event`, `enabled`, `last_status`, `last_response_time_ms`
- API endpoints under `/api/webhooks`:
  - `POST /api/webhooks` – create
  - `GET /api/webhooks` – list
  - `GET /api/webhooks/{id}` – get
  - `PUT /api/webhooks/{id}` – update
  - `DELETE /api/webhooks/{id}` – delete
  - `POST /api/webhooks/{id}/test` – enqueue a test webhook send
- Celery task `send_webhook`:
  - Reads webhook config from DB.
  - Sends POST with JSON payload `{ "event": ..., "data": {...} }`.
  - Records `last_status` and `last_response_time_ms` in the database.
- UI can be extended to list/add/edit/test/delete webhooks (API endpoints already exist).

---

## Local Setup (WSL / Linux / macOS)

### 1. Clone & enter the project

```bash
git clone https://github.com/<your-username>/product_importer.git
cd product_importer
