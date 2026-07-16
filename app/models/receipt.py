from typing   import List, Optional
from pydantic import BaseModel


class ReceiptItem(BaseModel):
    """영수증 단일 품목."""
    name:  str
    qty:   int   = 1
    price: int   = 0
    unit:  Optional[str] = None
    category: Optional[str] = None


class ReceiptVerifyRequest(BaseModel):
    """영수증 인증 최종 확정 요청."""
    scanId:      Optional[str]          = None   # /scan 에서 반환된 ID
    subjectId:   Optional[str]          = None   # 연계 식별자(선택)
    store:       Optional[str]          = None
    purchasedAt: Optional[str]          = None
    items:       List[ReceiptItem]      = []     # 사용자가 선택·편집한 품목 목록
