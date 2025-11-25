# Product Importer – Acme Inc

Backend coding assignment implementation for **Acme Inc – Product Importer**.

This is a FastAPI-based web application that:

- Uploads **large CSV files** (500k products) and imports them into a **PostgreSQL** database.
- Uses **Celery + Redis** to run the import **asynchronously** (no web timeouts).
- Shows **real-time progress** of the upload/import in the UI using **Server-Sent Events (SSE)**.
- Provides a **Product Management UI** (filter, paginate, create, update, delete).
- Supports **bulk delete** from the UI with confirmation.
- Provides **Webhook configuration & testing** via UI and asynchronous workers.

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
  - Webhook management stub 






