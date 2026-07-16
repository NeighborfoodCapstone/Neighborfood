from typing   import Optional
from pydantic import BaseModel, Field


class FridgeFromReceiptRequest(BaseModel):
    """영수증 인증 결과를 냉장고 항목으로 변환하는 요청."""
    receiptId: str  = Field(..., description="VERIFIED 상태의 영수증 ID")
    userId:    Optional[int] = Field(None, description="냉장고 소유자 회원 ID (선택)")


class FridgeStatusUpdateRequest(BaseModel):
    """냉장고 항목 상태 변경 요청."""
    status: str = Field(..., pattern=r"^(ACTIVE|CONSUMED|EXPIRED|DISCARDED)$")
