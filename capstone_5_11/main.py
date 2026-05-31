
# Receipt API extra imports
import os
import sqlite3
import hashlib
import secrets
from datetime import datetime, timezone
from typing import Optional
from urllib.parse import urlparse, parse_qs
from fastapi import Request
from pydantic import BaseModel

# 마지막 수정 : 2026.05.26
# Neighborfood FastAPI: 휴대폰 인증 API + QR 거래 인증 API

import hashlib
import os
import random
import secrets
import sqlite3
from datetime import datetime, timedelta, timezone
from typing import Optional
from urllib.parse import parse_qs, urlparse

from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
AUTH_DB_PATH = os.path.join(BASE_DIR, "auth.db")
QR_DB_PATH = os.path.join(BASE_DIR, "qr_auth.db")
RECEIPT_DB_PATH = os.path.join(BASE_DIR, "receipt.db")

app = FastAPI(title="NeighborFood Auth API")

# 로컬 개발용 CORS 설정
# 배포 시에는 allow_origins를 실제 프론트 도메인으로 제한해야 한다.
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)


# =========================================================
# 공통 / 휴대폰 인증 DB
# =========================================================
def get_auth_conn() -> sqlite3.Connection:
    return sqlite3.connect(AUTH_DB_PATH)


def init_auth_db() -> None:
    with get_auth_conn() as conn:
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS auth_codes (
                phone_number TEXT PRIMARY KEY,
                code TEXT NOT NULL,
                expiry_time TEXT NOT NULL
            )
            """
        )
        conn.commit()


class AuthRequest(BaseModel):
    phone_number: str = Field(
        ...,
        pattern=r"^010-\d{4}-\d{4}$",
        description="010-XXXX-XXXX 형식",
    )


class VerifyRequest(BaseModel):
    phone_number: str
    code: str = Field(..., min_length=6, max_length=6)


@app.post("/request-auth")
async def request_auth(request: AuthRequest):
    auth_code = str(random.randint(100000, 999999))
    expiry = (datetime.now() + timedelta(minutes=5)).isoformat()

    with get_auth_conn() as conn:
        conn.execute(
            """
            INSERT OR REPLACE INTO auth_codes (phone_number, code, expiry_time)
            VALUES (?, ?, ?)
            """,
            (request.phone_number, auth_code, expiry),
        )
        conn.commit()

    # 시연용: 실제 배포 시에는 응답에서 auth_code를 제거하고 SMS API로만 발송한다.
    print(f"\n[SMS 발송] {request.phone_number} → 인증번호: [{auth_code}] (만료: 5분)\n")

    return {
        "message": "인증번호가 발송되었습니다.",
        "auth_code": auth_code,
    }


@app.post("/verify-auth")
async def verify_auth(req: VerifyRequest):
    with get_auth_conn() as conn:
        row = conn.execute(
            "SELECT code, expiry_time FROM auth_codes WHERE phone_number = ?",
            (req.phone_number,),
        ).fetchone()

    if not row:
        raise HTTPException(
            status_code=404,
            detail="인증 요청 기록이 없습니다. 인증요청을 먼저 눌러 주세요.",
        )

    saved_code, expiry_str = row

    if datetime.fromisoformat(expiry_str) < datetime.now():
        raise HTTPException(
            status_code=410,
            detail="인증번호가 만료되었습니다. 재전송 후 다시 시도해 주세요.",
        )

    if saved_code != req.code:
        raise HTTPException(
            status_code=400,
            detail="인증번호가 일치하지 않습니다. 다시 확인해 주세요.",
        )

    with get_auth_conn() as conn:
        conn.execute(
            "DELETE FROM auth_codes WHERE phone_number = ?",
            (req.phone_number,),
        )
        conn.commit()

    print(f"\n[인증 완료] {req.phone_number}\n")
    return {"message": "인증이 완료되었습니다.", "verified": True}


# =========================================================
# QR 거래 인증 API
# =========================================================
def qr_get_conn() -> sqlite3.Connection:
    conn = sqlite3.connect(QR_DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def qr_now_utc() -> datetime:
    return datetime.now(timezone.utc)


def qr_to_iso(dt: datetime) -> str:
    return dt.astimezone(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def qr_from_iso(value: str) -> datetime:
    return datetime.fromisoformat(value.replace("Z", "+00:00"))


def qr_hash_token(token: str) -> str:
    return hashlib.sha256(token.encode("utf-8")).hexdigest()


def qr_parse_token(raw_value: str) -> str:
    if not raw_value:
        return ""

    value = raw_value.strip()
    if value.startswith("http://") or value.startswith("https://"):
        parsed = urlparse(value)
        query = parse_qs(parsed.query)

        if "token" in query and query["token"]:
            return query["token"][0]

        path_parts = [part for part in parsed.path.split("/") if part]
        if path_parts:
            return path_parts[-1]

    return value


def qr_row_to_dict(row: sqlite3.Row) -> dict:
    return {
        "id": row["id"],
        "subjectId": row["subject_id"],
        "purpose": row["purpose"],
        "status": row["status"],
        "issuedAt": row["issued_at"],
        "expiresAt": row["expires_at"],
        "usedAt": row["used_at"],
        "lastScannedAt": row["last_scanned_at"],
    }


def qr_init_db() -> None:
    with qr_get_conn() as conn:
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS qr_sessions (
                id TEXT PRIMARY KEY,
                subject_id TEXT NOT NULL,
                purpose TEXT NOT NULL,
                token_hash TEXT NOT NULL UNIQUE,
                status TEXT NOT NULL DEFAULT 'ISSUED'
                    CHECK (status IN ('ISSUED', 'VERIFIED', 'EXPIRED')),
                issued_at TEXT NOT NULL,
                expires_at TEXT NOT NULL,
                used_at TEXT,
                last_scanned_at TEXT,
                scanner_ip TEXT,
                scanner_user_agent TEXT,
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL
            )
            """
        )
        conn.execute(
            """
            CREATE INDEX IF NOT EXISTS idx_qr_sessions_subject_issued
            ON qr_sessions (subject_id, issued_at)
            """
        )
        conn.execute(
            """
            CREATE INDEX IF NOT EXISTS idx_qr_sessions_status_expires
            ON qr_sessions (status, expires_at)
            """
        )
        conn.execute(
            """
            CREATE INDEX IF NOT EXISTS idx_qr_sessions_token_hash
            ON qr_sessions (token_hash)
            """
        )
        conn.commit()


def qr_expire_old_sessions() -> None:
    current_time = qr_to_iso(qr_now_utc())
    with qr_get_conn() as conn:
        conn.execute(
            """
            UPDATE qr_sessions
            SET status = 'EXPIRED', updated_at = ?
            WHERE status = 'ISSUED' AND expires_at < ?
            """,
            (current_time, current_time),
        )
        conn.commit()


class QrIssueRequest(BaseModel):
    subjectId: str
    purpose: str = "pickup_confirm"
    ttlSeconds: int = 300


class QrVerifyRequest(BaseModel):
    token: Optional[str] = None
    rawValue: Optional[str] = None


@app.on_event("startup")
def startup() -> None:
    init_auth_db()
    qr_init_db()


@app.get("/api/qr/health")
def qr_health():
    qr_init_db()
    return {"ok": True, "message": "QR API is running"}


@app.post("/api/qr/request")
def issue_qr(body: QrIssueRequest):
    qr_init_db()

    subject_id = body.subjectId.strip()
    if not subject_id:
        return {"ok": False, "message": "subjectId가 비어 있습니다."}

    ttl = max(60, min(int(body.ttlSeconds or 300), 900))
    session_id = f"qrs_{secrets.token_hex(8)}"
    raw_token = secrets.token_urlsafe(32)
    token_hash = qr_hash_token(raw_token)

    issued_at = qr_now_utc()
    expires_at = issued_at + timedelta(seconds=ttl)
    issued_at_text = qr_to_iso(issued_at)
    expires_at_text = qr_to_iso(expires_at)

    with qr_get_conn() as conn:
        conn.execute(
            """
            INSERT INTO qr_sessions (
                id,
                subject_id,
                purpose,
                token_hash,
                status,
                issued_at,
                expires_at,
                used_at,
                last_scanned_at,
                scanner_ip,
                scanner_user_agent,
                created_at,
                updated_at
            )
            VALUES (?, ?, ?, ?, 'ISSUED', ?, ?, NULL, NULL, NULL, NULL, ?, ?)
            """,
            (
                session_id,
                subject_id,
                body.purpose,
                token_hash,
                issued_at_text,
                expires_at_text,
                issued_at_text,
                issued_at_text,
            ),
        )
        conn.commit()

    verify_url = f"http://127.0.0.1:8000/api/qr/verify/{raw_token}"

    return {
        "ok": True,
        "session": {
            "id": session_id,
            "subjectId": subject_id,
            "purpose": body.purpose,
            "status": "ISSUED",
            "issuedAt": issued_at_text,
            "expiresAt": expires_at_text,
            "usedAt": None,
            "lastScannedAt": None,
            "token": raw_token,
            "verifyUrl": verify_url,
        },
    }


@app.post("/api/qr/verify")
def verify_qr(body: QrVerifyRequest, request: Request):
    qr_init_db()
    qr_expire_old_sessions()

    raw_value = body.token or body.rawValue or ""
    token = qr_parse_token(raw_value)

    if not token:
        return {
            "ok": False,
            "result": "not_found",
            "message": "QR 토큰이 비어 있습니다.",
        }

    token_hash = qr_hash_token(token)
    scanned_at = qr_to_iso(qr_now_utc())
    scanner_ip = request.client.host if request.client else None
    scanner_user_agent = request.headers.get("user-agent")

    with qr_get_conn() as conn:
        row = conn.execute(
            "SELECT * FROM qr_sessions WHERE token_hash = ?",
            (token_hash,),
        ).fetchone()

        if row is None:
            return {
                "ok": False,
                "result": "not_found",
                "message": "저장된 인증 세션을 찾을 수 없습니다.",
            }

        conn.execute(
            """
            UPDATE qr_sessions
            SET last_scanned_at = ?, scanner_ip = ?, scanner_user_agent = ?, updated_at = ?
            WHERE id = ?
            """,
            (scanned_at, scanner_ip, scanner_user_agent, scanned_at, row["id"]),
        )
        conn.commit()

        row = conn.execute(
            "SELECT * FROM qr_sessions WHERE id = ?",
            (row["id"],),
        ).fetchone()

        if row["status"] == "EXPIRED":
            return {
                "ok": False,
                "result": "expired",
                "message": "만료된 QR입니다.",
                "session": qr_row_to_dict(row),
            }

        if row["status"] == "VERIFIED":
            return {
                "ok": False,
                "result": "already_used",
                "message": "이미 사용된 QR입니다.",
                "session": qr_row_to_dict(row),
            }

        if qr_from_iso(row["expires_at"]) < qr_now_utc():
            conn.execute(
                """
                UPDATE qr_sessions
                SET status = 'EXPIRED', updated_at = ?
                WHERE id = ?
                """,
                (scanned_at, row["id"]),
            )
            conn.commit()

            expired = conn.execute(
                "SELECT * FROM qr_sessions WHERE id = ?",
                (row["id"],),
            ).fetchone()

            return {
                "ok": False,
                "result": "expired",
                "message": "만료된 QR입니다.",
                "session": qr_row_to_dict(expired),
            }

        conn.execute(
            """
            UPDATE qr_sessions
            SET status = 'VERIFIED',
                used_at = ?,
                last_scanned_at = ?,
                scanner_ip = ?,
                scanner_user_agent = ?,
                updated_at = ?
            WHERE id = ?
            """,
            (
                scanned_at,
                scanned_at,
                scanner_ip,
                scanner_user_agent,
                scanned_at,
                row["id"],
            ),
        )
        conn.commit()

        updated = conn.execute(
            "SELECT * FROM qr_sessions WHERE id = ?",
            (row["id"],),
        ).fetchone()

    return {
        "ok": True,
        "result": "verified",
        "message": "QR 인증이 완료되었습니다.",
        "session": qr_row_to_dict(updated),
    }


@app.get("/api/qr/verify/{token}")
def verify_qr_by_url(token: str, request: Request):
    body = QrVerifyRequest(token=token)
    return verify_qr(body, request)


@app.get("/api/qr/history")
def get_qr_history(limit: int = 20):
    qr_init_db()
    qr_expire_old_sessions()

    limit = max(1, min(int(limit or 20), 50))

    with qr_get_conn() as conn:
        rows = conn.execute(
            """
            SELECT *
            FROM qr_sessions
            ORDER BY issued_at DESC
            LIMIT ?
            """,
            (limit,),
        ).fetchall()

    return {
        "ok": True,
        "items": [qr_row_to_dict(row) for row in rows],
    }


@app.delete("/api/qr/history")
def clear_qr_history():
    """로컬 개발 편의용: QR 이력 초기화."""
    qr_init_db()
    with qr_get_conn() as conn:
        conn.execute("DELETE FROM qr_sessions")
        conn.commit()
    return {"ok": True, "message": "QR 이력이 초기화되었습니다."}

# =========================================================
# 영수증 SQLite API
# =========================================================
def receipt_get_conn() -> sqlite3.Connection:
    conn = sqlite3.connect(RECEIPT_DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


def receipt_now_utc() -> datetime:
    return datetime.now(timezone.utc)


def receipt_to_iso(dt: datetime) -> str:
    return dt.astimezone(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def receipt_hash_token(token: str) -> str:
    return hashlib.sha256(token.encode("utf-8")).hexdigest()


def receipt_parse_token(raw_value: str) -> str:
    if not raw_value:
        return ""

    value = raw_value.strip()

    if value.startswith("http://") or value.startswith("https://"):
        parsed = urlparse(value)
        query = parse_qs(parsed.query)

        if "token" in query and query["token"]:
            return query["token"][0]

        path_parts = [part for part in parsed.path.split("/") if part]
        if path_parts:
            return path_parts[-1]

    return value


def receipt_init_db() -> None:
    with receipt_get_conn() as conn:
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS receipts (
                id TEXT PRIMARY KEY,
                trade_id TEXT NOT NULL,
                buyer_id TEXT NOT NULL,
                seller_id TEXT NOT NULL,
                title TEXT NOT NULL,
                total_amount INTEGER NOT NULL,
                payment_method TEXT NOT NULL,
                status TEXT NOT NULL DEFAULT 'ISSUED'
                    CHECK (status IN ('ISSUED', 'CONFIRMED', 'CANCELED')),
                token_hash TEXT NOT NULL UNIQUE,
                issued_at TEXT NOT NULL,
                confirmed_at TEXT,
                canceled_at TEXT,
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL
            )
            """
        )

        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS receipt_items (
                id TEXT PRIMARY KEY,
                receipt_id TEXT NOT NULL,
                name TEXT NOT NULL,
                quantity INTEGER NOT NULL,
                unit_price INTEGER NOT NULL,
                amount INTEGER NOT NULL,
                created_at TEXT NOT NULL,
                FOREIGN KEY (receipt_id) REFERENCES receipts(id) ON DELETE CASCADE
            )
            """
        )

        conn.execute(
            """
            CREATE INDEX IF NOT EXISTS idx_receipts_trade_issued
            ON receipts (trade_id, issued_at)
            """
        )

        conn.execute(
            """
            CREATE INDEX IF NOT EXISTS idx_receipts_status_issued
            ON receipts (status, issued_at)
            """
        )

        conn.execute(
            """
            CREATE INDEX IF NOT EXISTS idx_receipts_token_hash
            ON receipts (token_hash)
            """
        )

        conn.commit()


def receipt_items_for(conn: sqlite3.Connection, receipt_id: str) -> list:
    rows = conn.execute(
        """
        SELECT id, name, quantity, unit_price, amount, created_at
        FROM receipt_items
        WHERE receipt_id = ?
        ORDER BY created_at ASC, id ASC
        """,
        (receipt_id,),
    ).fetchall()

    return [
        {
            "id": row["id"],
            "name": row["name"],
            "quantity": row["quantity"],
            "unitPrice": row["unit_price"],
            "amount": row["amount"],
            "createdAt": row["created_at"],
        }
        for row in rows
    ]


def receipt_row_to_dict(row: sqlite3.Row, items: list | None = None, include_token: str | None = None) -> dict:
    data = {
        "id": row["id"],
        "tradeId": row["trade_id"],
        "buyerId": row["buyer_id"],
        "sellerId": row["seller_id"],
        "title": row["title"],
        "totalAmount": row["total_amount"],
        "paymentMethod": row["payment_method"],
        "status": row["status"],
        "issuedAt": row["issued_at"],
        "confirmedAt": row["confirmed_at"],
        "canceledAt": row["canceled_at"],
        "createdAt": row["created_at"],
        "updatedAt": row["updated_at"],
        "items": items or [],
    }

    if include_token:
        data["token"] = include_token

    return data


class ReceiptItemRequest(BaseModel):
    name: str = Field(..., min_length=1)
    quantity: int = Field(..., gt=0)
    unitPrice: int = Field(..., ge=0)


class ReceiptIssueRequest(BaseModel):
    tradeId: str = Field(..., min_length=1)
    buyerId: str = Field(..., min_length=1)
    sellerId: str = Field(..., min_length=1)
    title: str = Field("거래 영수증", min_length=1)
    paymentMethod: str = Field("TRANSFER", min_length=1)
    items: list[ReceiptItemRequest] = Field(..., min_length=1)


class ReceiptConfirmRequest(BaseModel):
    receiptId: Optional[str] = None
    token: Optional[str] = None
    rawValue: Optional[str] = None


@app.on_event("startup")
def receipt_startup() -> None:
    receipt_init_db()


@app.get("/api/receipt/health")
def receipt_health():
    receipt_init_db()
    return {"ok": True, "message": "Receipt API is running"}


@app.post("/api/receipt/issue")
def issue_receipt(body: ReceiptIssueRequest, request: Request):
    receipt_init_db()

    trade_id = body.tradeId.strip()
    buyer_id = body.buyerId.strip()
    seller_id = body.sellerId.strip()
    title = body.title.strip()
    payment_method = body.paymentMethod.strip().upper()

    if not trade_id or not buyer_id or not seller_id:
        return {"ok": False, "message": "tradeId, buyerId, sellerId는 필수입니다."}

    receipt_items = []
    total_amount = 0

    for item in body.items:
        item_name = item.name.strip()
        quantity = int(item.quantity)
        unit_price = int(item.unitPrice)
        amount = quantity * unit_price

        if not item_name:
            return {"ok": False, "message": "품목명이 비어 있습니다."}

        receipt_items.append(
            {
                "id": f"rci_{secrets.token_hex(8)}",
                "name": item_name,
                "quantity": quantity,
                "unitPrice": unit_price,
                "amount": amount,
            }
        )
        total_amount += amount

    receipt_id = f"rcp_{secrets.token_hex(8)}"
    raw_token = secrets.token_urlsafe(32)
    token_hash = receipt_hash_token(raw_token)
    now_text = receipt_to_iso(receipt_now_utc())

    with receipt_get_conn() as conn:
        conn.execute(
            """
            INSERT INTO receipts (
                id, trade_id, buyer_id, seller_id, title,
                total_amount, payment_method, status, token_hash,
                issued_at, confirmed_at, canceled_at, created_at, updated_at
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, 'ISSUED', ?, ?, NULL, NULL, ?, ?)
            """,
            (
                receipt_id,
                trade_id,
                buyer_id,
                seller_id,
                title,
                total_amount,
                payment_method,
                token_hash,
                now_text,
                now_text,
                now_text,
            ),
        )

        for item in receipt_items:
            conn.execute(
                """
                INSERT INTO receipt_items (
                    id, receipt_id, name, quantity, unit_price, amount, created_at
                )
                VALUES (?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    item["id"],
                    receipt_id,
                    item["name"],
                    item["quantity"],
                    item["unitPrice"],
                    item["amount"],
                    now_text,
                ),
            )

        conn.commit()

        row = conn.execute(
            "SELECT * FROM receipts WHERE id = ?",
            (receipt_id,),
        ).fetchone()

        items = receipt_items_for(conn, receipt_id)

    base_url = str(request.base_url).rstrip("/")
    view_url = f"{base_url}/api/receipt/token/{raw_token}"

    receipt = receipt_row_to_dict(row, items=items, include_token=raw_token)
    receipt["viewUrl"] = view_url

    return {
        "ok": True,
        "message": "영수증이 발급되었습니다.",
        "receipt": receipt,
    }


@app.get("/api/receipt/token/{token}")
def get_receipt_by_token(token: str):
    receipt_init_db()

    parsed_token = receipt_parse_token(token)
    token_hash = receipt_hash_token(parsed_token)

    with receipt_get_conn() as conn:
        row = conn.execute(
            "SELECT * FROM receipts WHERE token_hash = ?",
            (token_hash,),
        ).fetchone()

        if row is None:
            return {
                "ok": False,
                "result": "not_found",
                "message": "영수증을 찾을 수 없습니다.",
            }

        items = receipt_items_for(conn, row["id"])

    return {
        "ok": True,
        "receipt": receipt_row_to_dict(row, items=items),
    }


@app.get("/api/receipt/history")
def get_receipt_history(limit: int = 20):
    receipt_init_db()

    limit = max(1, min(int(limit or 20), 50))

    with receipt_get_conn() as conn:
        rows = conn.execute(
            """
            SELECT * FROM receipts
            ORDER BY issued_at DESC
            LIMIT ?
            """,
            (limit,),
        ).fetchall()

        items = []
        for row in rows:
            receipt_items = receipt_items_for(conn, row["id"])
            items.append(receipt_row_to_dict(row, items=receipt_items))

    return {
        "ok": True,
        "items": items,
    }


@app.post("/api/receipt/confirm")
def confirm_receipt(body: ReceiptConfirmRequest):
    receipt_init_db()

    receipt_id = (body.receiptId or "").strip()
    raw_value = body.token or body.rawValue or ""
    token = receipt_parse_token(raw_value)

    with receipt_get_conn() as conn:
        if receipt_id:
            row = conn.execute(
                "SELECT * FROM receipts WHERE id = ?",
                (receipt_id,),
            ).fetchone()
        elif token:
            token_hash = receipt_hash_token(token)
            row = conn.execute(
                "SELECT * FROM receipts WHERE token_hash = ?",
                (token_hash,),
            ).fetchone()
        else:
            return {
                "ok": False,
                "result": "bad_request",
                "message": "receiptId 또는 token이 필요합니다.",
            }

        if row is None:
            return {
                "ok": False,
                "result": "not_found",
                "message": "영수증을 찾을 수 없습니다.",
            }

        if row["status"] == "CONFIRMED":
            items = receipt_items_for(conn, row["id"])
            return {
                "ok": False,
                "result": "already_confirmed",
                "message": "이미 확인된 영수증입니다.",
                "receipt": receipt_row_to_dict(row, items=items),
            }

        if row["status"] == "CANCELED":
            items = receipt_items_for(conn, row["id"])
            return {
                "ok": False,
                "result": "canceled",
                "message": "취소된 영수증입니다.",
                "receipt": receipt_row_to_dict(row, items=items),
            }

        now_text = receipt_to_iso(receipt_now_utc())

        conn.execute(
            """
            UPDATE receipts
            SET status = 'CONFIRMED',
                confirmed_at = ?,
                updated_at = ?
            WHERE id = ?
            """,
            (now_text, now_text, row["id"]),
        )
        conn.commit()

        updated = conn.execute(
            "SELECT * FROM receipts WHERE id = ?",
            (row["id"],),
        ).fetchone()
        items = receipt_items_for(conn, updated["id"])

    return {
        "ok": True,
        "result": "confirmed",
        "message": "영수증 확인이 완료되었습니다.",
        "receipt": receipt_row_to_dict(updated, items=items),
    }


@app.get("/api/receipt/{receipt_id}")
def get_receipt_by_id(receipt_id: str):
    receipt_init_db()

    with receipt_get_conn() as conn:
        row = conn.execute(
            "SELECT * FROM receipts WHERE id = ?",
            (receipt_id,),
        ).fetchone()

        if row is None:
            return {
                "ok": False,
                "result": "not_found",
                "message": "영수증을 찾을 수 없습니다.",
            }

        items = receipt_items_for(conn, receipt_id)

    return {
        "ok": True,
        "receipt": receipt_row_to_dict(row, items=items),
    }


@app.delete("/api/receipt/history")
def clear_receipt_history():
    receipt_init_db()

    with receipt_get_conn() as conn:
        conn.execute("DELETE FROM receipt_items")
        conn.execute("DELETE FROM receipts")
        conn.commit()

    return {
        "ok": True,
        "message": "영수증 이력이 초기화되었습니다.",
    }

# python main.py 로 직접 실행할 때 사용
if __name__ == "__main__":
    import uvicorn

    uvicorn.run("main:app", host="127.0.0.1", port=8000, reload=True)
