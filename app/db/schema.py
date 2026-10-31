"""Read-only PostgreSQL startup contract for the reviewed 001–003 migrations.

Update this contract whenever an application migration changes required columns.
This does not replace ledger, constraint, permission, or RLS verification.
"""

REQUIRED_COLUMNS = {
    "auth_codes": frozenset(
        "phone_number code expiry_time".split()
    ),
    "conversation_members": frozenset(
        "conversation_id user_id last_read_id joined_at".split()
    ),
    "conversations": frozenset(
        "id post_id host_id guest_id created_at kind".split()
    ),
    "fridge_items": frozenset(
        "id user_id receipt_id source item_name qty unit price category store_name purchased_at status created_at updated_at expiry_date memo quantity_text".split()
    ),
    "groupbuy_participants": frozenset(
        "post_id user_id joined_at".split()
    ),
    "location_verify_sessions": frozenset(
        "id subject_id target_lat target_lng target_address radius_m status current_lat current_lng current_accuracy distance_m qr_session_id verified_at created_at updated_at transaction_id settlement_id".split()
    ),
    "manner_ratings": frozenset(
        "id transaction_id rater_id ratee_id score comment created_at".split()
    ),
    "messages": frozenset(
        "id conversation_id sender_id content created_at read_at is_system".split()
    ),
    "neighborfood_schema_version": frozenset(
        "version".split()
    ),
    "notices": frozenset(
        "id author_id title content created_at".split()
    ),
    "ocr_guard_audit": frozenset(
        "id actor_id enabled created_at".split()
    ),
    "ocr_guard_settings": frozenset(
        "id enabled user_daily_limit user_monthly_limit global_monthly_limit updated_at".split()
    ),
    "ocr_requests": frozenset(
        "id user_id idempotency_key image_hash status scan_id object_name storage_kind created_at updated_at".split()
    ),
    "portone_quick_test_payments": frozenset(
        "payment_id user_id amount store_id channel_key status created_at checked_at".split()
    ),
    "portone_test_payments": frozenset(
        "payment_id user_id settlement_id amount store_id channel_key status created_at checked_at".split()
    ),
    "posts": frozenset(
        "id type title description category images address lat lng author_id status created_at expires_at gb_target gb_current gb_price exchange_want appointment_place appointment_at appointment_lat appointment_lng".split()
    ),
    "qr_sessions": frozenset(
        "id subject_id purpose token_hash status issued_at expires_at used_at last_scanned_at scanner_ip scanner_user_agent created_at updated_at transaction_id settlement_id scanner_id location_session_id".split()
    ),
    "qr_verification_events": frozenset(
        "id qr_session_id actor_id outcome created_at".split()
    ),
    "receipts": frozenset(
        "id subject_id store_name purchased_at items selected_items total status trust_delta ocr_engine image_path scanned_at verified_at created_at updated_at safe_ocr_text ocr_result_json raw_ocr_json shopping_matches_json shopping_match_status shopping_matched_at fridge_added_at".split()
    ),
    "reports": frozenset(
        "id reporter_id target_type target_id reason status created_at".split()
    ),
    "sessions": frozenset(
        "token user_id expires_at created_at".split()
    ),
    "settlement_shares": frozenset(
        "settlement_id user_id amount status gps_verified quality_agreed auto_confirmed paid_at created_at".split()
    ),
    "settlements": frozenset(
        "id post_id requester_id total_amount account_info status appointment_place appointment_at appointment_lat appointment_lng created_at completed_at".split()
    ),
    "transactions": frozenset(
        "id post_id provider_id receiver_id status qr_session_id receipt_id appointment_at created_at completed_at settlement_id".split()
    ),
    "users": frozenset(
        "id login_id password_hash phone_number nickname profile_image trust_score role status neighborhood neighborhood_verified_at email bio interests dietary created_at updated_at".split()
    ),
    "wishlists": frozenset(
        "user_id post_id created_at".split()
    ),
}


def validate_postgres_schema(connection) -> None:
    """Fail before initialization if an application table/column is unavailable."""
    rows = connection.conn.execute(
        "SELECT table_name, column_name FROM information_schema.columns "
        "WHERE table_schema = 'public' AND table_name = ANY(%s)",
        (list(REQUIRED_COLUMNS),),
    ).fetchall()
    actual = {}
    for row in rows:
        actual.setdefault(row['table_name'], set()).add(row['column_name'])

    missing = []
    for table, columns in REQUIRED_COLUMNS.items():
        if table not in actual:
            missing.append(table)
        else:
            missing.extend(f"{table}.{column}" for column in sorted(columns - actual[table]))
    if missing:
        raise RuntimeError(
            "PostgreSQL schema is incomplete or inaccessible: " + ", ".join(missing)
            + ". Review Supabase migration history and docs/SUPABASE_MIGRATION.md before deploying; "
              "do not replay migrations on an existing schema."
        )
