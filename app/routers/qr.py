import secrets
from datetime         import timedelta
from fastapi          import APIRouter, Request
from app.core.utils   import now_utc, to_iso, from_iso, hash_token, parse_token
from app.db           import qr_db
from app.models.qr    import QrIssueRequest, QrVerifyRequest

router = APIRouter()


@router.post("/request")
def issue_qr(body: QrIssueRequest):
    qr_db.init_qr_db()

    subject_id = body.subjectId.strip()
    if not subject_id:
        return {"ok": False, "message": "subjectId가 비어 있습니다."}

    ttl        = max(60, min(body.ttlSeconds, 900))
    session_id = f"qrs_{secrets.token_hex(8)}"
    raw_token  = secrets.token_urlsafe(32)
    token_hash = hash_token(raw_token)

    issued_at       = now_utc()
    expires_at      = issued_at + timedelta(seconds=ttl)
    issued_at_text  = to_iso(issued_at)
    expires_at_text = to_iso(expires_at)

    with qr_db.get_conn() as conn:
        conn.execute("""
            INSERT INTO qr_sessions (
                id, subject_id, purpose, token_hash, status,
                issued_at, expires_at,
                used_at, last_scanned_at, scanner_ip, scanner_user_agent,
                created_at, updated_at
            )
            VALUES (?, ?, ?, ?, 'ISSUED', ?, ?, NULL, NULL, NULL, NULL, ?, ?)
        """, (
            session_id, subject_id, body.purpose, token_hash,
            issued_at_text, expires_at_text,
            issued_at_text, issued_at_text,
        ))
        conn.commit()

    verify_url = f"http://127.0.0.1:8000/api/qr/verify/{raw_token}"

    return {
        "ok": True,
        "session": {
            "id":            session_id,
            "subjectId":     subject_id,
            "purpose":       body.purpose,
            "status":        "ISSUED",
            "issuedAt":      issued_at_text,
            "expiresAt":     expires_at_text,
            "usedAt":        None,
            "lastScannedAt": None,
            "token":         raw_token,
            "verifyUrl":     verify_url,
        },
    }


@router.post("/verify")
def verify_qr(body: QrVerifyRequest, request: Request):
    qr_db.init_qr_db()
    qr_db.expire_old_sessions()

    raw_value = body.token or body.rawValue or ""
    token     = parse_token(raw_value)

    if not token:
        return {"ok": False, "result": "invalid_input", "message": "QR 토큰이 비어 있습니다."}

    token_hash = hash_token(token)
    scanned_at = to_iso(now_utc())
    scanner_ip = request.client.host if request.client else None
    scanner_ua = request.headers.get("user-agent")

    with qr_db.get_conn() as conn:
        row = conn.execute(
            "SELECT * FROM qr_sessions WHERE token_hash = ?", (token_hash,)
        ).fetchone()

        if row is None:
            return {"ok": False, "result": "not_found", "message": "저장된 인증 세션을 찾을 수 없습니다."}

        conn.execute("""
            UPDATE qr_sessions
            SET last_scanned_at = ?, scanner_ip = ?, scanner_user_agent = ?, updated_at = ?
            WHERE id = ?
        """, (scanned_at, scanner_ip, scanner_ua, scanned_at, row["id"]))
        conn.commit()

        row = conn.execute(
            "SELECT * FROM qr_sessions WHERE id = ?", (row["id"],)
        ).fetchone()

        if row["status"] == "EXPIRED":
            return {"ok": False, "result": "expired", "message": "만료된 QR입니다.",
                    "session": qr_db.row_to_dict(row)}

        if row["status"] == "VERIFIED":
            return {"ok": False, "result": "already_used", "message": "이미 사용된 QR입니다.",
                    "session": qr_db.row_to_dict(row)}

        if from_iso(row["expires_at"]) < now_utc():
            conn.execute(
                "UPDATE qr_sessions SET status='EXPIRED', updated_at=? WHERE id=?",
                (scanned_at, row["id"]),
            )
            conn.commit()
            row = conn.execute(
                "SELECT * FROM qr_sessions WHERE id=?", (row["id"],)
            ).fetchone()
            return {"ok": False, "result": "expired", "message": "만료된 QR입니다.",
                    "session": qr_db.row_to_dict(row)}

        conn.execute("""
            UPDATE qr_sessions
            SET status = 'VERIFIED', used_at = ?, last_scanned_at = ?,
                scanner_ip = ?, scanner_user_agent = ?, updated_at = ?
            WHERE id = ?
        """, (scanned_at, scanned_at, scanner_ip, scanner_ua, scanned_at, row["id"]))
        conn.commit()

        updated = conn.execute(
            "SELECT * FROM qr_sessions WHERE id=?", (row["id"],)
        ).fetchone()

    return {
        "ok":      True,
        "result":  "verified",
        "message": "QR 인증이 완료되었습니다.",
        "session": qr_db.row_to_dict(updated),
    }


@router.get("/verify/{token}")
def verify_qr_by_url(token: str, request: Request):
    return verify_qr(QrVerifyRequest(token=token), request)


@router.post("/verify/{token}")
def verify_qr_post_by_url(token: str, request: Request):
    return verify_qr(QrVerifyRequest(token=token), request)


@router.get("/history")
def get_qr_history(limit: int = 20):
    qr_db.init_qr_db()
    qr_db.expire_old_sessions()
    limit = max(1, min(limit, 50))

    with qr_db.get_conn() as conn:
        rows = conn.execute(
            "SELECT * FROM qr_sessions ORDER BY issued_at DESC LIMIT ?", (limit,)
        ).fetchall()

    return {"ok": True, "items": [qr_db.row_to_dict(r) for r in rows]}