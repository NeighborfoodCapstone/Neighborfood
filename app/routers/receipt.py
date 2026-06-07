import json
import os
import secrets
from fastapi             import APIRouter, HTTPException, UploadFile, File, Query
from app.config          import UPLOAD_DIR, RECEIPT_TRUST_DELTA
from app.core.utils      import now_utc, to_iso
from app.db              import receipt_db
from app.models.receipt  import ReceiptVerifyRequest

router = APIRouter()


@router.post("/scan")
async def scan_receipt(
    file:      UploadFile = File(...),
    subjectId: str        = Query(""),
):
    receipt_db.init_receipt_db()

    allowed_ext = {".jpg", ".jpeg", ".png", ".webp", ".gif"}
    ext = os.path.splitext(file.filename or "")[1].lower()
    if ext not in allowed_ext:
        raise HTTPException(status_code=400, detail=f"허용되지 않은 확장자: {ext}")

    new_name   = f"receipt_{secrets.token_hex(8)}{ext}"
    image_path = os.path.join(UPLOAD_DIR, new_name)
    with open(image_path, "wb") as out:
        out.write(await file.read())

    raw_text   = receipt_db.ocr_text(image_path)
    safe_text  = receipt_db.redact_pii(raw_text)
    parsed     = receipt_db.parse_receipt(safe_text) if safe_text else {"items": []}
    ocr_engine = "tesseract"

    if not parsed.get("items"):
        parsed     = receipt_db.demo_items()
        ocr_engine = "demo"

    scan_id    = f"rcpt_{secrets.token_hex(8)}"
    now        = to_iso(now_utc())
    items_json = json.dumps(parsed["items"], ensure_ascii=False)

    with receipt_db.get_conn() as conn:
        conn.execute("""
            INSERT INTO receipts (
                id, subject_id, store_name, purchased_at, items, selected_items,
                total, status, trust_delta, ocr_engine, image_path,
                scanned_at, verified_at, created_at, updated_at
            )
            VALUES (?, ?, ?, ?, ?, '[]', ?, 'SCANNED', 0, ?, ?, ?, NULL, ?, ?)
        """, (
            scan_id, subjectId.strip() or None, parsed.get("store"),
            parsed.get("purchasedAt"), items_json, parsed.get("total"),
            ocr_engine, new_name, now, now, now,
        ))
        conn.commit()

    print(f"\n[영수증 분석] {scan_id} · 엔진={ocr_engine} · 항목 {len(parsed['items'])}개\n")

    return {
        "ok": True,
        "scan": {
            "id":          scan_id,
            "subjectId":   subjectId.strip() or None,
            "store":       parsed.get("store"),
            "purchasedAt": parsed.get("purchasedAt"),
            "total":       parsed.get("total"),
            "items":       parsed["items"],
            "ocrEngine":   ocr_engine,
            "imageUrl":    f"/uploads/{new_name}",
            "status":      "SCANNED",
            "scannedAt":   now,
        },
    }


@router.post("/verify")
def verify_receipt(body: ReceiptVerifyRequest):
    receipt_db.init_receipt_db()

    selected = [item.dict() for item in body.items]
    if not selected:
        return {"ok": False, "result": "no_items", "message": "인증할 항목을 1개 이상 선택하세요."}

    now           = to_iso(now_utc())
    selected_json = json.dumps(selected, ensure_ascii=False)
    trust_delta   = RECEIPT_TRUST_DELTA

    with receipt_db.get_conn() as conn:
        row        = None
        receipt_id = None

        if body.scanId:
            row = conn.execute(
                "SELECT * FROM receipts WHERE id = ?", (body.scanId,)
            ).fetchone()

        if row is not None:
            if row["status"] == "VERIFIED":
                return {
                    "ok":      False,
                    "result":  "already_used",
                    "message": "이미 인증에 사용된 영수증입니다.",
                    "receipt": receipt_db.row_to_dict(row),
                }
            conn.execute("""
                UPDATE receipts
                SET status = 'VERIFIED', selected_items = ?, trust_delta = ?,
                    store_name   = COALESCE(?, store_name),
                    purchased_at = COALESCE(?, purchased_at),
                    verified_at  = ?, updated_at = ?
                WHERE id = ?
            """, (selected_json, trust_delta,
                  body.store, body.purchasedAt,
                  now, now, row["id"]))
            receipt_id = row["id"]
        else:
            receipt_id = f"rcpt_{secrets.token_hex(8)}"
            conn.execute("""
                INSERT INTO receipts (
                    id, subject_id, store_name, purchased_at, items, selected_items,
                    total, status, trust_delta, ocr_engine, image_path,
                    scanned_at, verified_at, created_at, updated_at
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, 'VERIFIED', ?, 'manual', NULL, ?, ?, ?, ?)
            """, (
                receipt_id, (body.subjectId or "").strip() or None,
                body.store, body.purchasedAt,
                selected_json, selected_json,
                sum(i.get("price", 0) for i in selected),
                trust_delta, now, now, now, now,
            ))

        conn.commit()
        updated = conn.execute(
            "SELECT * FROM receipts WHERE id = ?", (receipt_id,)
        ).fetchone()

    print(f"\n[영수증 인증 완료] {receipt_id} · 항목 {len(selected)}개 · 신뢰온도 +{trust_delta}°\n")

    return {
        "ok":         True,
        "result":     "verified",
        "message":    "영수증 인증이 완료되었습니다.",
        "trustDelta": trust_delta,
        "receipt":    receipt_db.row_to_dict(updated),
    }


@router.get("/history")
def get_receipt_history(limit: int = 20):
    receipt_db.init_receipt_db()
    limit = max(1, min(limit, 50))

    with receipt_db.get_conn() as conn:
        rows = conn.execute(
            "SELECT * FROM receipts ORDER BY scanned_at DESC LIMIT ?", (limit,)
        ).fetchall()

    return {"ok": True, "items": [receipt_db.row_to_dict(r) for r in rows]}