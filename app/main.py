# app/main.py
import os
import uuid
import shutil
from typing import Optional
from fastapi import FastAPI, UploadFile, File, Depends, HTTPException, Query
from fastapi.responses import HTMLResponse, StreamingResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
from .webhooks import router as webhooks_router
from sqlalchemy.orm import Session
import redis
import json

from .database import SessionLocal
from . import crud, schemas, webhooks
from .tasks import import_csv
from .utils import validate_csv_header, safe_remove

# Required CSV columns for our import staging
REQUIRED_COLUMNS = ["sku", "name", "description"]

# App setup
app = FastAPI(title="Product Importer (no-docker)")

# CORS (useful during development; tweak origins for production)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Mount static files (simple UI)
static_dir = os.path.join(os.path.dirname(__file__), "static")
if os.path.isdir(static_dir):
    app.mount("/static", StaticFiles(directory=static_dir), name="static")

# include webhooks router
#app.include_router(webhooks.router)
app.include_router(webhooks_router)

# Redis connection for SSE pub/sub (used by tasks to publish progress)
REDIS_URL = os.getenv("REDIS_URL", "redis://localhost:6379/0")
r = redis.Redis.from_url(REDIS_URL, decode_responses=True)

# Upload dir (local). Ensure this exists and is writable by the process.
UPLOAD_DIR = os.getenv("UPLOAD_DIR", "/tmp/importer_uploads")
os.makedirs(UPLOAD_DIR, exist_ok=True)

# Dependency: DB session
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

@app.get("/", response_class=HTMLResponse)
def index():
    index_path = os.path.join(static_dir, "index.html")
    if os.path.exists(index_path):
        with open(index_path, "r", encoding="utf-8") as f:
            return HTMLResponse(f.read())
    return HTMLResponse("<html><body><h1>Product Importer</h1><p>No UI found.</p></body></html>")

@app.post("/api/upload")
async def upload_csv(file: UploadFile = File(...)):
    """
    Stream-upload the CSV to local disk and enqueue a Celery import task.
    Returns a task_id client can use to subscribe to progress via /api/events?task_id=...
    """
    # basic validation of content-type
    if not file.filename or not file.filename.lower().endswith(".csv"):
        raise HTTPException(status_code=400, detail="Only .csv files are supported")

    task_id = str(uuid.uuid4())
    safe_name = f"{task_id}_{os.path.basename(file.filename)}"
    dest_path = os.path.join(UPLOAD_DIR, safe_name)

    # Stream write to disk (1 MB chunks)
    try:
        with open(dest_path, "wb") as dest:
            while True:
                chunk = await file.read(1024 * 1024)
                if not chunk:
                    break
                dest.write(chunk)
    except Exception as e:
        # cleanup if write fails
        safe_remove(dest_path)
        raise HTTPException(status_code=500, detail=f"Failed saving upload: {e}")

    # quick header validation (fail fast before enqueuing)
    is_valid, missing = validate_csv_header(dest_path, REQUIRED_COLUMNS)
    if not is_valid:
        # remove file to avoid stale uploads
        safe_remove(dest_path)
        missing_str = ", ".join(missing)
        raise HTTPException(status_code=400, detail=f"CSV missing required columns: {missing_str}")

    # enqueue Celery import task (worker will pick it up)
    try:
        import_csv.delay(dest_path, task_id)
    except Exception as e:
        # cleanup local file if queueing fails
        safe_remove(dest_path)
        raise HTTPException(status_code=500, detail=f"Failed enqueuing import task: {e}")

    return {"task_id": task_id, "message": "Upload accepted and processing started."}

@app.get("/api/events")
def sse_events(task_id: str):
    """
    SSE endpoint: subscribe to redis channel "import:{task_id}" and stream messages to client.
    Messages are expected to be small strings or JSON-serializable content published by worker.
    """
    channel = f"import:{task_id}"
    pubsub = r.pubsub()
    pubsub.subscribe(channel)

    def event_generator():
        try:
            for message in pubsub.listen():
                # message example: {'type': 'message', 'pattern': None, 'channel': 'import:...', 'data': '...'}
                if message is None:
                    continue
                if message.get("type") != "message":
                    continue
                data = message.get("data")
                # ensure we send JSON-safe string lines
                try:
                    # if worker publishes JSON-like string or dict, forward as-is
                    if isinstance(data, str):
                        yield f"data: {data}\n\n"
                    else:
                        yield f"data: {json.dumps(data)}\n\n"
                except Exception:
                    # fallback to repr
                    yield f"data: {repr(data)}\n\n"

                # optional: stop after success or error keywords to close connection
                try:
                    text = data if isinstance(data, str) else json.dumps(data)
                    if "complete" in text or "error" in text:
                        break
                except Exception:
                    pass
        finally:
            try:
                pubsub.close()
            except Exception:
                pass

    return StreamingResponse(event_generator(), media_type="text/event-stream")

# -----------------------
# Product CRUD & list API
# -----------------------

@app.get("/api/products")
def list_products(skip: int = 0, limit: int = 50, sku: Optional[str] = None,
                  name: Optional[str] = None, active: Optional[bool] = None,
                  description: Optional[str] = None, db: Session = Depends(get_db)):
    filters = {}
    if sku:
        filters["sku"] = sku
    if name:
        filters["name"] = name
    if active is not None:
        filters["active"] = active
    if description:
        filters["description"] = description
    items, total = crud.get_products(db, skip=skip, limit=limit, filters=filters)
    # SQLAlchemy models are returned; FastAPI will try to JSON serialize them.
    # To avoid leaking internal fields, convert to dicts (simple approach)
    def to_dict(obj):
        return {
            "id": obj.id,
            "sku": obj.sku,
            "name": obj.name,
            "description": obj.description,
            "price_cents": obj.price_cents,
            "active": obj.active,
            "created_at": obj.created_at.isoformat() if obj.created_at else None,
            "updated_at": obj.updated_at.isoformat() if obj.updated_at else None
        }
    return {"total": total, "items": [to_dict(i) for i in items]}

@app.post("/api/products")
def create_product(payload: schemas.ProductCreate, db: Session = Depends(get_db)):
    obj = crud.create_product(db, payload)
    return obj

@app.put("/api/products/{product_id}")
def update_product(product_id: int, payload: schemas.ProductUpdate, db: Session = Depends(get_db)):
    obj = crud.update_product(db, product_id, payload.dict(exclude_unset=True))
    if not obj:
        raise HTTPException(status_code=404, detail="Product not found")
    return obj

@app.delete("/api/products/{product_id}")
def delete_product(product_id: int, db: Session = Depends(get_db)):
    obj = crud.delete_product(db, product_id)
    if not obj:
        raise HTTPException(status_code=404, detail="Product not found")
    return {"status": "deleted"}

@app.post("/api/products/bulk-delete")
def bulk_delete(confirm: bool = Query(..., description="set to true to confirm bulk delete"), db: Session = Depends(get_db)):
    if not confirm:
        raise HTTPException(status_code=400, detail="Confirmation required to delete all products")
    crud.delete_all_products(db)
    return {"status": "all deleted"}

# Health check
@app.get("/health")
def health():
    return {"status": "ok"}

# include webhooks endpoints (router already included above), just expose base path
# app.include_router(webhooks.router)  # already done at top

# Helpful debug endpoint to list upload dir contents (dev only)
@app.get("/_debug/uploads")
def debug_uploads():
    try:
        files = os.listdir(UPLOAD_DIR)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
    return {"upload_dir": UPLOAD_DIR, "files": files}
