# app/webhooks.py
import time
from typing import List
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from .database import get_db
from . import crud, schemas
from .tasks import send_webhook  # Celery task (worker)

router = APIRouter(prefix="/api/webhooks", tags=["webhooks"])

@router.post("/", response_model=schemas.WebhookOut)
def create_hook(payload: schemas.WebhookCreate, db: Session = Depends(get_db)):
    return crud.create_webhook(db, payload)

@router.get("/", response_model=List[schemas.WebhookOut])
def list_hooks(skip: int = 0, limit: int = 100, db: Session = Depends(get_db)):
    return crud.get_webhooks(db, skip=skip, limit=limit)

@router.get("/{id}", response_model=schemas.WebhookOut)
def get_hook(id: int, db: Session = Depends(get_db)):
    hook = crud.get_webhook(db, id)
    if not hook:
        raise HTTPException(status_code=404, detail="Webhook not found")
    return hook

@router.put("/{id}", response_model=schemas.WebhookOut)
def update_hook(id: int, patch: schemas.WebhookUpdate, db: Session = Depends(get_db)):
    obj = crud.update_webhook(db, id, patch)
    if not obj:
        raise HTTPException(status_code=404, detail="Webhook not found")
    return obj

@router.delete("/{id}")
def delete_hook(id: int, db: Session = Depends(get_db)):
    obj = crud.delete_webhook(db, id)
    if not obj:
        raise HTTPException(status_code=404, detail="Webhook not found")
    return {"status": "deleted"}

@router.post("/{id}/test")
def test_hook(id: int, db: Session = Depends(get_db)):
    hook = crud.get_webhook(db, id)
    if not hook:
        raise HTTPException(status_code=404, detail="Webhook not found")
    # enqueue a background send_webhook task; returns queued response immediately
    send_webhook.delay(hook.id, hook.event, {"test": True})
    return {"status": "queued"}
