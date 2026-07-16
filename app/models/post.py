from pydantic import BaseModel, Field
from typing   import Optional, List


class PostCreate(BaseModel):
    type: str = Field(
        ...,
        pattern=r'^(share|exchange|groupbuy)$',
        description="share | exchange | groupbuy",
    )
    title:         str             = Field(..., min_length=1, max_length=100)
    description:   Optional[str]   = ""
    category:      Optional[str]   = None
    images:        List[str]       = []
    address:       Optional[str]   = None
    lat:           Optional[float] = None
    lng:           Optional[float] = None
    # author_id는 더 이상 클라이언트가 정하지 않습니다(서버가 세션 회원 id로 대체).
    # 구버전 프런트 호환을 위해 받기만 하고 무시하므로 선택값으로 둡니다.
    author_id:     Optional[str]   = None
    expires_at:    Optional[str]   = None
    # 공동구매 전용
    gb_target:     Optional[int]   = None
    gb_price:      Optional[int]   = None
    # 교환 전용
    exchange_want: Optional[str]   = None
