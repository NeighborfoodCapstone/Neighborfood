from pydantic import BaseModel, Field


class QrIssueRequest(BaseModel):
    """QR 세션 발급 요청."""
    subjectId:  str = Field(..., min_length=1, description="대상 식별자 (예: user_42, post_7)")
    purpose:    str = Field("pickup_confirm", description="발행 목적")
    ttlSeconds: int = Field(300, ge=60, le=900, description="유효 시간(초). 60~900 사이")


class QrVerifyRequest(BaseModel):
    """QR 검증 요청: 스캐너가 읽은 토큰 또는 URL."""
    token:    str | None = None
    rawValue: str | None = None   # 카메라 라이브러리가 원본 QR값을 보내는 필드명
