from fastapi import APIRouter, HTTPException, Query

from app.db import fridge_db
from app.models.fridge import FridgeFromReceiptRequest, FridgeStatusUpdateRequest


router = APIRouter()


@router.get("/health")
def fridge_health():
    fridge_db.init_fridge_db()
    return {"ok": True, "message": "fridge api ready"}


@router.post("/from-receipt")
def add_fridge_items_from_receipt(body: FridgeFromReceiptRequest):
    try:
        result = fridge_db.add_from_receipt(body.receiptId, body.userId)
        return {"ok": True, "result": "added", **result}
    except LookupError as exc:
        raise HTTPException(status_code=404, detail=str(exc))
    except PermissionError as exc:
        raise HTTPException(status_code=409, detail=str(exc))
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))


@router.get("/items")
def get_fridge_items(
    userId: int | None = Query(None),
    status: str = Query("ACTIVE"),
    limit: int = Query(50),
):
    return {"ok": True, "items": fridge_db.list_items(userId, status, limit)}


@router.patch("/items/{item_id}/status")
def update_fridge_item_status(item_id: str, body: FridgeStatusUpdateRequest):
    try:
        item = fridge_db.update_status(item_id, body.status)
        return {"ok": True, "item": item}
    except LookupError as exc:
        raise HTTPException(status_code=404, detail=str(exc))
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))
