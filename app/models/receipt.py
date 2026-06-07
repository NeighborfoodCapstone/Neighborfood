from pydantic import BaseModel
from typing   import Optional, List


class ReceiptItemModel(BaseModel):
    name:  str
    qty:   int = 1
    price: int = 0


class ReceiptVerifyRequest(BaseModel):
    scanId:      Optional[str]              = None
    subjectId:   Optional[str]              = None
    store:       Optional[str]              = None
    purchasedAt: Optional[str]              = None
    items:       List[ReceiptItemModel]     = []
