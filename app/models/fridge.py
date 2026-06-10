from typing import Optional
from pydantic import BaseModel, Field


class FridgeFromReceiptRequest(BaseModel):
    receiptId: str = Field(..., min_length=4)
    userId: Optional[int] = None


class FridgeStatusUpdateRequest(BaseModel):
    status: str = Field(..., min_length=3)
