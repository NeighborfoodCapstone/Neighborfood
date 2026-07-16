# -*- coding: utf-8 -*-
from __future__ import annotations

from fastapi import APIRouter, HTTPException, Request

from app.db.location_verify_db import (
    create_dummy_target,
    get_session,
    gps_check,
    init_location_verify_db,
    list_sessions,
    mark_qr_issued,
)

router = APIRouter()


@router.get("/health")
def health():
    init_location_verify_db()
    return {"ok": True, "message": "location verify api ok"}


@router.post("/dummy-target")
async def dummy_target(request: Request):
    init_location_verify_db()
    payload = await request.json()
    try:
        session = create_dummy_target(payload)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    return {"ok": True, "session": session}


@router.post("/{session_id}/gps-check")
async def gps_check_route(session_id: str, request: Request):
    init_location_verify_db()
    payload = await request.json()
    try:
        return gps_check(session_id, payload)
    except LookupError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/{session_id}/qr-issued")
async def qr_issued(session_id: str, request: Request):
    init_location_verify_db()
    payload = await request.json()
    try:
        session = mark_qr_issued(session_id, payload)
    except LookupError as e:
        raise HTTPException(status_code=404, detail=str(e))
    return {"ok": True, "session": session}


@router.get("/{session_id}")
def detail(session_id: str):
    init_location_verify_db()
    session = get_session(session_id)
    if not session:
        raise HTTPException(status_code=404, detail="location verify session not found")
    return {"ok": True, "session": session}


@router.get("/history/list")
def history(limit: int = 20):
    init_location_verify_db()
    return {"ok": True, "items": list_sessions(limit)}
