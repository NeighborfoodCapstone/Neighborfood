from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel

from app.core.deps import get_current_user
from app.db import fridge_db
from app.models.fridge import FridgeFromReceiptRequest, FridgeStatusUpdateRequest


router = APIRouter()


class FridgeManualItemRequest(BaseModel):
    name: str
    category: Optional[str] = None
    quantity: Optional[str] = None
    expiry_date: Optional[str] = None
    memo: Optional[str] = None


class FridgeManualItemUpdate(BaseModel):
    name: Optional[str] = None
    category: Optional[str] = None
    quantity: Optional[str] = None
    expiry_date: Optional[str] = None
    memo: Optional[str] = None


@router.get("/health")
def fridge_health():
    fridge_db.init_fridge_db()
    return {"ok": True, "message": "fridge api ready"}


@router.post("/from-receipt")
def add_fridge_items_from_receipt(
    body: FridgeFromReceiptRequest,
    current_user=Depends(get_current_user),
):
    try:
        result = fridge_db.add_from_receipt(body.receiptId, current_user["id"])
        return {"ok": True, "result": "added", **result}
    except LookupError as exc:
        raise HTTPException(status_code=404, detail=str(exc))
    except PermissionError as exc:
        raise HTTPException(status_code=409, detail=str(exc))
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))


@router.get("/items")
def get_fridge_items(
    status: str = Query("ACTIVE"),
    limit: int = Query(50),
    current_user=Depends(get_current_user),
):
    return {"ok": True, "items": fridge_db.list_items_v2(current_user["id"], status, limit)}


@router.post("/items")
def create_fridge_item(
    body: FridgeManualItemRequest,
    current_user=Depends(get_current_user),
):
    try:
        item = fridge_db.add_manual_item(
            user_id=current_user["id"],
            name=body.name,
            category=body.category,
            quantity=body.quantity,
            expiry_date=body.expiry_date,
            memo=body.memo,
        )
        return {"ok": True, "item": item}
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))


@router.patch("/items/{item_id}")
def update_fridge_item(
    item_id: str,
    body: FridgeManualItemUpdate,
    current_user=Depends(get_current_user),
):
    try:
        item = fridge_db.update_manual_item(
            item_id=item_id,
            user_id=current_user["id"],
            name=body.name,
            category=body.category,
            quantity=body.quantity,
            expiry_date=body.expiry_date,
            memo=body.memo,
        )
        return {"ok": True, "item": item}
    except LookupError as exc:
        raise HTTPException(status_code=404, detail=str(exc))
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))


@router.delete("/items/{item_id}")
def delete_fridge_item(
    item_id: str,
    current_user=Depends(get_current_user),
):
    try:
        fridge_db.delete_manual_item(item_id, current_user["id"])
        return {"ok": True}
    except LookupError as exc:
        raise HTTPException(status_code=404, detail=str(exc))


@router.patch("/items/{item_id}/status")
def update_fridge_item_status(
    item_id: str,
    body: FridgeStatusUpdateRequest,
    current_user=Depends(get_current_user),
):
    try:
        item = fridge_db.update_status(item_id, body.status, current_user["id"])
        return {"ok": True, "item": item}
    except LookupError as exc:
        raise HTTPException(status_code=404, detail=str(exc))
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))
