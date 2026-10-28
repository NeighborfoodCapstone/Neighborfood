import json
import hashlib
from io import BytesIO
import os
import secrets
import sqlite3
import tempfile
from app import storage
from app.core.deps import get_current_user
from fastapi.responses import FileResponse, RedirectResponse

from fastapi import APIRouter, File, Header, HTTPException, Query, UploadFile, Depends
from PIL import Image, UnidentifiedImageError

from app.config import DATA_DIR, RECEIPT_TRUST_DELTA, UPLOAD_DIR
from app.core.utils import now_utc, to_iso
from app.db import ocr_guard, receipt_db
from app.models.receipt import ReceiptVerifyRequest

router = APIRouter()


@router.get("/health")
def receipt_health():
    receipt_db.init_receipt_db()
    return {"ok": True, "message": "receipt api ok"}


def _valid_image(data: bytes, ext: str, content_type: str) -> bool:
    kinds = {
        ".jpg": ("image/jpeg", "JPEG"), ".jpeg": ("image/jpeg", "JPEG"),
        ".png": ("image/png", "PNG"),
        ".tif": ("image/tiff", "TIFF"), ".tiff": ("image/tiff", "TIFF"),
    }
    expected = kinds.get(ext)
    if not expected or content_type.lower() != expected[0]:
        return False
    try:
        with Image.open(BytesIO(data)) as image:
            if image.format != expected[1] or image.width * image.height > 24_000_000:
                return False
            image.verify()
        return True
    except (UnidentifiedImageError, Image.DecompressionBombError, OSError, ValueError, SyntaxError):
        return False


def _scan_response(row):
    scan = receipt_db.row_to_dict(row)
    name = scan["imagePath"]
    image_url = storage.signed_receipt_url(name) if storage.enabled() else f"/api/receipt/image/{name}"
    return {"ok": True, "scan": {
        "id": scan["id"], "subjectId": scan["subjectId"], "store": scan["store"],
        "purchasedAt": scan["purchasedAt"], "total": scan["total"], "items": scan["items"],
        "ocrEngine": scan["ocrEngine"], "ocrTextPreview": (scan["safeOcrText"] or "")[:600],
        "imageUrl": image_url, "status": scan["status"], "scannedAt": scan["scannedAt"],
    }}


@router.post("/scan")
async def scan_receipt(
    file: UploadFile = File(...),
    subjectId: str = Query(""),
    idempotency_key: str = Header("", alias="Idempotency-Key"),
    user: dict = Depends(get_current_user),
):
    """Authenticate, validate and reserve a shared budget before any OCR call."""
    receipt_db.init_receipt_db()
    if subjectId and subjectId != str(user["id"]):
        raise HTTPException(403, "본인의 영수증만 등록할 수 있습니다.")
    ext = os.path.splitext(file.filename or "")[1].lower()
    data = await file.read(storage.MAX_BYTES + 1)
    if len(data) > storage.MAX_BYTES:
        raise HTTPException(413, "영수증 이미지는 4MB 이하여야 합니다.")
    if not _valid_image(data, ext, file.content_type or ""):
        raise HTTPException(400, "JPEG, PNG 또는 TIFF 이미지(24MP 이하)만 분석할 수 있습니다. 파일을 다시 선택해 주세요.")
    try:
        reservation = ocr_guard.reserve(user["id"], idempotency_key, hashlib.sha256(data).hexdigest())
    except HTTPException:
        raise
    except Exception:
        raise HTTPException(503, "OCR 안전 설정을 확인할 수 없어 분석을 중단했습니다. 수동 입력을 이용해 주세요.") from None
    if reservation.get("replay"):
        with receipt_db.get_conn() as conn:
            row = conn.execute("SELECT * FROM receipts WHERE id = ? AND subject_id = ?",
                               (reservation["replay"], str(user["id"]))).fetchone()
        if not row:
            raise HTTPException(503, "이전 OCR 결과를 확인할 수 없습니다.")
        return _scan_response(row)

    request_id = reservation["id"]
    new_name = f"receipt_{secrets.token_hex(8)}{ext}"
    try:
        fd, image_path = tempfile.mkstemp(suffix=ext)
        try:
            with os.fdopen(fd, "wb") as out:
                out.write(data)
            ocr_guard.mark_sent(request_id, new_name, "supabase" if storage.enabled() else "local")
            ocr_engine, safe_text, ocr_debug = receipt_db.run_ocr(image_path)
        finally:
            os.unlink(image_path)
        clova = (ocr_debug or {}).get("clova", ocr_debug or {})
        if clova.get("enabled") is False or clova.get("ok") is False:
            raise HTTPException(503, "OCR 결과를 확인할 수 없습니다. 같은 요청을 중복 호출하지 않았습니다. 수동 입력을 이용해 주세요.")
        parsed = receipt_db.parse_receipt(safe_text) if safe_text else {"items": []}
        if not parsed.get("items"):
            parsed = {**receipt_db.empty_receipt_result(), **parsed, "items": []}
            ocr_engine = f"{ocr_engine}_empty"
        if storage.enabled():
            storage.save("receipts", new_name, data)
        else:
            private_dir = os.path.join(DATA_DIR, "receipts")
            os.makedirs(private_dir, exist_ok=True)
            with open(os.path.join(private_dir, new_name), "wb") as out:
                out.write(data)
        scan_id = f"rcpt_{secrets.token_hex(8)}"
        now = to_iso(now_utc())
        result_json = json.dumps({"engine": ocr_engine, "store": parsed.get("store"),
                                  "purchasedAt": parsed.get("purchasedAt"), "total": parsed.get("total"),
                                  "itemCount": len(parsed["items"])}, ensure_ascii=False)
        with receipt_db.get_conn() as conn:
            conn.execute("""
                INSERT INTO receipts (
                    id, subject_id, store_name, purchased_at, items, selected_items,
                    total, status, trust_delta, ocr_engine, image_path,
                    safe_ocr_text, ocr_result_json, raw_ocr_json,
                    scanned_at, verified_at, created_at, updated_at
                ) VALUES (?, ?, ?, ?, ?, '[]', ?, 'SCANNED', 0, ?, ?, ?, ?, '{}', ?, NULL, ?, ?)
            """, (scan_id, str(user["id"]), parsed.get("store"), parsed.get("purchasedAt"),
                  json.dumps(parsed["items"], ensure_ascii=False), parsed.get("total"), ocr_engine,
                  new_name, safe_text, result_json, now, now, now))
            updated = conn.execute("""UPDATE ocr_requests SET status = 'completed', scan_id = ?, updated_at = ?
                                      WHERE id = ? AND status = 'sent'""", (scan_id, now, request_id))
            if updated.rowcount != 1:
                raise RuntimeError("OCR reservation state changed")
            row = conn.execute("SELECT * FROM receipts WHERE id = ?", (scan_id,)).fetchone()
            conn.commit()
    except Exception as exc:
        try:
            ocr_guard.mark_failed(request_id)
        except Exception:
            pass
        if isinstance(exc, HTTPException):
            raise
        raise HTTPException(503, "OCR 처리 또는 저장에 실패했습니다. 수동 입력을 이용해 주세요.") from None
    return _scan_response(row)


@router.post("/verify")
def verify_receipt(body: ReceiptVerifyRequest, user: dict = Depends(get_current_user)):
    """사용자가 검토/수정/선택한 항목을 최종 인증하여 DB에 저장한다."""
    receipt_db.init_receipt_db()
    if body.subjectId and body.subjectId != str(user["id"]):
        raise HTTPException(403, "본인의 영수증만 인증할 수 있습니다.")
    body.subjectId = str(user["id"])
    selected = [item.dict() for item in body.items]
    if not selected:
        return {"ok": False, "result": "no_items", "message": "인증할 항목을 1개 이상 선택하세요."}

    now = to_iso(now_utc())
    selected_json = json.dumps(selected, ensure_ascii=False)
    # Manual input and scans with no recognized items are not independent proof.
    trust_delta = 0.0

    with receipt_db.get_conn() as conn:
        row = None
        receipt_id = None

        if body.scanId:
            row = conn.execute("SELECT * FROM receipts WHERE id = ?", (body.scanId,)).fetchone()

        if body.scanId and row is None:
            raise HTTPException(404, "영수증을 찾을 수 없습니다.")
        if row is not None and row["subject_id"] != str(user["id"]):
            raise HTTPException(403, "본인의 영수증만 인증할 수 있습니다.")
        if row is not None:
            if row["status"] == "VERIFIED":
                return {
                    "ok": False,
                    "result": "already_used",
                    "message": "이미 인증에 사용된 영수증입니다.",
                    "receipt": receipt_db.row_to_dict(row),
                }
            if row["status"] != "SCANNED":
                raise HTTPException(409, "인증할 수 없는 영수증 상태입니다.")
            if row["ocr_engine"] in ("clova", "tesseract") and receipt_db.row_to_dict(row)["items"]:
                trust_delta = RECEIPT_TRUST_DELTA

            changed = conn.execute("""
                UPDATE receipts
                SET status = 'VERIFIED',
                    selected_items = ?,
                    trust_delta = ?,
                    store_name = COALESCE(?, store_name),
                    purchased_at = COALESCE(?, purchased_at),
                    verified_at = ?,
                    updated_at = ?
                WHERE id = ? AND status = 'SCANNED'
            """, (selected_json, trust_delta, body.store, body.purchasedAt, now, now, row["id"]))
            if changed.rowcount != 1:
                current = conn.execute("SELECT * FROM receipts WHERE id = ?", (row["id"],)).fetchone()
                return {"ok": False, "result": "already_used", "message": "이미 인증에 사용된 영수증입니다.",
                        "receipt": receipt_db.row_to_dict(current)}
            receipt_id = row["id"]
        else:
            receipt_id = f"rcpt_{secrets.token_hex(8)}"
            conn.execute("""
                INSERT INTO receipts (
                    id, subject_id, store_name, purchased_at, items, selected_items,
                    total, status, trust_delta, ocr_engine, image_path,
                    safe_ocr_text, ocr_result_json,
                    scanned_at, verified_at, created_at, updated_at
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, 'VERIFIED', ?, 'manual', NULL, NULL, '{}', ?, ?, ?, ?)
            """, (
                receipt_id,
                (body.subjectId or "").strip() or None,
                body.store,
                body.purchasedAt,
                selected_json,
                selected_json,
                sum(i.get("price", 0) for i in selected),
                trust_delta,
                now,
                now,
                now,
                now,
            ))
        if trust_delta:
            suffix = "" if isinstance(conn, sqlite3.Connection) else " FOR UPDATE"
            profile = conn.execute("SELECT trust_score FROM users WHERE id = ?" + suffix, (user["id"],)).fetchone()
            trust_delta = max(0.0, min(trust_delta, 99.0 - float(profile["trust_score"])))
            if trust_delta:
                conn.execute("UPDATE users SET trust_score = trust_score + ? WHERE id = ?",
                             (trust_delta, user["id"]))
            conn.execute("UPDATE receipts SET trust_delta = ? WHERE id = ?", (trust_delta, receipt_id))

        conn.commit()
        updated = conn.execute("SELECT * FROM receipts WHERE id = ?", (receipt_id,)).fetchone()

    print(f"\n[영수증 인증 완료] {receipt_id} · 항목 {len(selected)}개 · 신뢰온도 +{trust_delta}°\n")

    return {
        "ok": True,
        "result": "verified",
        "message": "영수증 인증이 완료되었습니다.",
        "trustDelta": trust_delta,
        "receipt": receipt_db.row_to_dict(updated),
    }


@router.get("/history")
def get_receipt_history(limit: int = 20, user: dict = Depends(get_current_user)):
    receipt_db.init_receipt_db()
    limit = max(1, min(limit, 50))
    with receipt_db.get_conn() as conn:
        rows = conn.execute(
            "SELECT * FROM receipts WHERE subject_id = ? ORDER BY scanned_at DESC LIMIT ?",
            (str(user["id"]), limit),
        ).fetchall()
    return {"ok": True, "items": [receipt_db.row_to_dict(r) for r in rows]}


@router.get("/image/{name}")
def receipt_image(name: str, user: dict = Depends(get_current_user)):
    with receipt_db.get_conn() as conn:
        row=conn.execute("SELECT subject_id FROM receipts WHERE image_path = ?",(name,)).fetchone()
    if not row or row["subject_id"] != str(user["id"]):
        raise HTTPException(404,"영수증 이미지를 찾을 수 없습니다.")
    if storage.enabled():
        return RedirectResponse(storage.signed_receipt_url(name), status_code=307)
    path = os.path.join(DATA_DIR, "receipts", os.path.basename(name))
    if not os.path.isfile(path):
        # Pre-migration local receipts remain readable only after the ownership check.
        path = os.path.join(UPLOAD_DIR, os.path.basename(name))
    if not os.path.isfile(path):
        raise HTTPException(404, "영수증 이미지를 찾을 수 없습니다.")
    return FileResponse(path)
