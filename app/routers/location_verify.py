# -*- coding: utf-8 -*-
"""
location_verify.py — GPS 위치 인증 라우터

보안 강화 사항 (2026-07-09 점검 적용):
  - 전 엔드포인트 Bearer 토큰 인증 필수 (get_current_user)
  - 세션 생성 시 subject_id 서버 강제 고정 (요청 바디 값을 무시)
  - 세션 조회·검증·수정 시 소유자 검증 (_assert_owner)
  - 이력(list_sessions) 본인 세션만 반환
"""
from __future__ import annotations

from typing import Optional

from fastapi  import APIRouter, Depends, HTTPException
from pydantic import BaseModel

from app.core.deps             import get_current_user
from app.db.location_verify_db import (
    create_dummy_target,
    get_session,
    gps_check        as db_gps_check,
    list_sessions    as db_list_sessions,
    mark_qr_issued   as db_mark_qr_issued,
)

router = APIRouter()


# ── Pydantic 요청 모델 ────────────────────────────────────────────────────────

class DummyTargetRequest(BaseModel):
    lat:      float
    lng:      float
    accuracy: Optional[float] = None
    address:  Optional[str]   = None
    radiusM:  float            = 100   # 거래 지점 허용 반경(100m, 프론트 UI와 동기화)
    # subjectId: 클라이언트 값 무시 — 서버가 로그인 uid로 강제 설정(보안)


class GpsCheckRequest(BaseModel):
    lat:            float
    lng:            float
    accuracy:       Optional[float] = None
    radiusM:        float            = 100    # 거래 지점 허용 반경(100m)
    accuracyLimitM: float            = 1500   # 시연용 GPS 정확도 허용치


class QrIssuedRequest(BaseModel):
    qrSessionId: Optional[str] = None


# ── 내부 헬퍼 ─────────────────────────────────────────────────────────────────

def _assert_owner(session: dict, user_id: int) -> None:
    """세션 소유자가 아니면 403.
    subject_id가 'demo_' 로 시작하는 데모 세션은 검증을 생략합니다."""
    sid = session.get("subject_id") or ""
    if sid.startswith("demo_"):
        return
    if sid != str(user_id):
        raise HTTPException(403, "본인 세션만 접근할 수 있습니다.")


# ── 엔드포인트 ────────────────────────────────────────────────────────────────

@router.post("/dummy-target")
async def create_target(body: DummyTargetRequest,
                        user: dict = Depends(get_current_user)):
    """GPS 위치 인증 세션 생성.
    subject_id는 서버가 현재 사용자 ID로 강제 고정합니다(보안)."""
    payload = body.dict()
    payload["subjectId"] = str(user["id"])   # 서버 강제 고정
    try:
        session = create_dummy_target(payload)
    except ValueError as exc:
        raise HTTPException(400, str(exc))
    return {"ok": True, "session": session}


@router.post("/{session_id}/gps-check")
async def gps_check_endpoint(session_id: str, body: GpsCheckRequest,
                              user: dict = Depends(get_current_user)):
    """현재 GPS 좌표로 거래 지점 반경을 검증합니다."""
    session = get_session(session_id)
    if not session:
        raise HTTPException(404, "GPS 세션을 찾을 수 없습니다.")
    _assert_owner(session, user["id"])
    try:
        result = db_gps_check(session_id, body.dict())
    except (LookupError, ValueError) as exc:
        raise HTTPException(400, str(exc))
    return {
        "ok":      result["ok"],
        "status":  result["status"],
        "message": result["message"],
        "session": result["session"],
    }


@router.post("/{session_id}/qr-issued")
async def qr_issued(session_id: str, body: QrIssuedRequest,
                    user: dict = Depends(get_current_user)):
    """GPS 세션에 QR 세션 ID를 연결하고 상태를 QR_ISSUED로 갱신합니다."""
    session = get_session(session_id)
    if not session:
        raise HTTPException(404, "GPS 세션을 찾을 수 없습니다.")
    _assert_owner(session, user["id"])
    payload = {}
    if body.qrSessionId:
        payload["qrSessionId"] = body.qrSessionId
    updated = db_mark_qr_issued(session_id, payload)
    return {"ok": True, "session": updated}


@router.get("/sessions")
async def list_sessions_endpoint(limit: int = 20,
                                  user: dict = Depends(get_current_user)):
    """본인 소유 GPS 인증 세션 이력. subject_id 필터 자동 적용."""
    sessions = db_list_sessions(limit=limit, subject_id=str(user["id"]))
    return {"ok": True, "sessions": sessions}


@router.get("/{session_id}")
async def get_session_detail(session_id: str,
                              user: dict = Depends(get_current_user)):
    """단일 GPS 세션 상세. 본인 세션만 허용합니다."""
    session = get_session(session_id)
    if not session:
        raise HTTPException(404, "GPS 세션을 찾을 수 없습니다.")
    _assert_owner(session, user["id"])
    return {"ok": True, "session": session}