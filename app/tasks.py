# app/tasks.py
import os
import re
import csv
import time
import redis
import psycopg2
import requests
from .celery_app import cel
from .database import SessionLocal
from . import crud

REDIS_URL = os.getenv("REDIS_URL", "redis://localhost:6379/0")
PG_DSN = os.getenv("DATABASE_URL", "postgresql://importer:importer@localhost:5432/importer")
r = redis.Redis.from_url(REDIS_URL, decode_responses=True)

def publish(task_id, payload):
    try:
        r.publish(f"import:{task_id}", str(payload))
    except Exception:
        pass

def _safe_table_name(task_id: str) -> str:
    t = task_id.lower().replace('-', '_')
    t = re.sub(r'[^a-z0-9_]', '_', t)
    return f"staging_{t}"

@cel.task(bind=True)
def import_csv(self, local_path: str, task_id: str, default_active: bool = True):
    conn = None
    cur = None
    try:
        publish(task_id, {"status": "saved", "message": "file saved on worker"})
        temp_table = _safe_table_name(task_id)

        # Read header to detect columns
        with open(local_path, newline='', encoding='utf-8') as fh:
            reader = csv.reader(fh)
            try:
                header = next(reader)
            except StopIteration:
                raise RuntimeError("Empty CSV file")
        header_cols = [h.strip().lower() for h in header]
        allowed = ["sku", "name", "description", "price_cents"]
        copy_cols = [c for c in allowed if c in header_cols]

        if "sku" not in copy_cols:
            raise RuntimeError("CSV must include 'sku' column")

        publish(task_id, {"status": "creating_staging", "table": temp_table, "copy_cols": copy_cols})

        conn = psycopg2.connect(PG_DSN)
        cur = conn.cursor()

        # create temp table with all possible columns
        cur.execute(f"""
            CREATE TEMP TABLE {temp_table} (
                sku text,
                name text,
                description text,
                price_cents integer
            ) ON COMMIT DROP;
        """)

        publish(task_id, {"status": "copying", "message": f"COPYing columns: {copy_cols}"})
        cols_sql = ", ".join(copy_cols)
        with open(local_path, "r", encoding="utf-8") as f:
            cur.copy_expert(f"COPY {temp_table} ({cols_sql}) FROM STDIN WITH CSV HEADER", f)

        publish(task_id, {"status": "deduplicating"})
        upsert_sql = f"""
        WITH uniq AS (
            SELECT sku, name, description, price_cents FROM (
                SELECT *, row_number() OVER (PARTITION BY lower(sku) ORDER BY ctid DESC) AS rn
                FROM {temp_table}
            ) t
            WHERE rn = 1
        )
        INSERT INTO products (sku, name, description, price_cents, active, created_at, updated_at)
        SELECT sku, name, description, price_cents, %s, now(), now()
        FROM uniq
        ON CONFLICT (sku_lower) DO UPDATE
          SET sku = EXCLUDED.sku,
              name = EXCLUDED.name,
              description = EXCLUDED.description,
              price_cents = EXCLUDED.price_cents,
              updated_at = now();
        """
        publish(task_id, {"status": "upserting"})
        cur.execute(upsert_sql, (default_active,))

        conn.commit()
        publish(task_id, {"status": "complete", "message": "Import complete"})

        try:
            os.remove(local_path)
        except Exception:
            pass
        return {"status": "ok"}
    except Exception as e:
        try:
            publish(task_id, {"status": "error", "message": str(e)})
        except Exception:
            pass
        if conn:
            try:
                conn.rollback()
            except Exception:
                pass
        raise
    finally:
        if cur:
            try:
                cur.close()
            except Exception:
                pass
        if conn:
            try:
                conn.close()
            except Exception:
                pass

@cel.task(bind=True)
def send_webhook(self, webhook_id: int, event: str, payload: dict):
    """
    Celery task to POST to configured webhook and update status in DB.
    """
    db = SessionLocal()
    try:
        hook = crud.get_webhook(db, webhook_id)
        if not hook or not hook.enabled:
            return {"status": "skipped"}
        url = hook.url
        start = time.time()
        try:
            resp = requests.post(url, json={"event": event, "data": payload}, timeout=10)
            elapsed = int((time.time() - start) * 1000)
            hook.last_status = str(resp.status_code)
            hook.last_response_time_ms = elapsed
            db.add(hook)
            db.commit()
            return {"status": "sent", "code": resp.status_code, "time_ms": elapsed}
        except Exception as e:
            elapsed = int((time.time() - start) * 1000)
            hook.last_status = f"error:{str(e)[:200]}"
            hook.last_response_time_ms = elapsed
            db.add(hook)
            db.commit()
            raise
    finally:
        db.close()
