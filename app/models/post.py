from pydantic import BaseModel, Field
from typing   import Optional, List


class PostCreate(BaseModel):
    type: str = Field(
        ...,
        pattern=r'^(share|exchange|groupbuy)$',
        description="share | exchange | groupbuy",
    )
    title:         str            = Field(..., min_length=1, max_length=100)
    description:   Optional[str]  = ""
    category:      Optional[str]  = None
    images:        List[str]      = []
    address:       Optional[str]  = None
    lat:           Optional[float] = None
    lng:           Optional[float] = None
    author_id:     str
    expires_at:    Optional[str]  = None
    # 공동구매 전용
    gb_target:     Optional[int]  = None
    gb_price:      Optional[int]  = None
    # 교환 전용
    exchange_want: Optional[str]  = None
