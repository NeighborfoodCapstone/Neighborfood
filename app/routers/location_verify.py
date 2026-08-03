# -*- coding: utf-8 -*-
from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Request

from app.core.deps import get_current_user
from app.db.location_verify_db import (
    create_dummy_target,
    get_session,
    gps_check,
    init_location_verify_db,
    list_sessions,
    mark_qr_issued,
)

router = APIRouter()


def _assert_owner(session: dict, user: dict) -> None:
    """세션 소유자 본인 또는 관리자만 접근을 허용합니다.
    (2026-07-09 점검: 기존에는 인증 자체가 없어 누구나 타인의 GPS 인증 세션을
    조회·조작할 수 있었던 문제를 수정)"""
    if user.get("role") == "admin":
        return
    if str(session.get("subject_id") or "") != str(user["id"]):
        raise HTTPException(status_code=403, detail="본인의 위치 인증 세션만 접근할 수 있습니다.")


@router.get("/health")
def health():
    init_location_verify_db()
    return {"ok": True, "message": "location verify api ok"}


@router.post("/dummy-target")
async def dummy_target(request: Request, user: dict = Depends(get_current_user)):
    init_location_verify_db()
    payload = await request.json()
    # subject_id는 클라이언트 입력을 신뢰하지 않고 로그인한 본인 id로 항상 고정합니다.
    # (기존에는 클라이언트가 임의 문자열을 보내거나 생략 시 "demo_pickup_..."로
    #  채워져 세션과 실제 사용자가 전혀 연결되지 않는 문제가 있었습니다.)
    payload = dict(payload or {})
    payload["subject_id"] = str(user["id"])
    try:
        session = create_dummy_target(payload)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    return {"ok": True, "session": session}


@router.post("/{session_id}/gps-check")
async def gps_check_route(session_id: str, request: Request, user: dict = Depends(get_current_user)):
    init_location_verify_db()
    existing = get_session(session_id)
    if not existing:
        raise HTTPException(status_code=404, detail="location verify session not found")
    _assert_owner(existing, user)
    payload = await request.json()
    try:
        return gps_check(session_id, payload)
    except LookupError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/{session_id}/qr-issued")
async def qr_issued(session_id: str, request: Request, user: dict = Depends(get_current_user)):
    init_location_verify_db()
    existing = get_session(session_id)
    if not existing:
        raise HTTPException(status_code=404, detail="location verify session not found")
    _assert_owner(existing, user)
    payload = await request.json()
    try:
        session = mark_qr_issued(session_id, payload)
    except LookupError as e:
        raise HTTPException(status_code=404, detail=str(e))
    return {"ok": True, "session": session}


@router.get("/{session_id}")
def detail(session_id: str, user: dict = Depends(get_current_user)):
    init_location_verify_db()
    session = get_session(session_id)
    if not session:
        raise HTTPException(status_code=404, detail="location verify session not found")
    _assert_owner(session, user)
    return {"ok": True, "session": session}


@router.get("/history/list")
def history(limit: int = 20, user: dict = Depends(get_current_user)):
    init_location_verify_db()
    # 관리자는 전체 이력을, 일반 사용자는 본인 세션만 조회합니다.
    # (기존에는 인증 자체가 없어 누구나 전체 사용자의 GPS 좌표 이력을 열람할 수 있었던 문제를 수정)
    subject_id = None if user.get("role") == "admin" else str(user["id"])
    return {"ok": True, "items": list_sessions(limit, subject_id=subject_id)}