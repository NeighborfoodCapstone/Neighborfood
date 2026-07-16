from pydantic import BaseModel, Field
from typing   import Optional, List


class ProfileUpdate(BaseModel):
    """프로필 수정 요청. 보낸 필드만 갱신합니다."""
    nickname:      Optional[str]       = Field(None, min_length=1, max_length=30)
    profile_image: Optional[str]       = Field(None, max_length=500)
    bio:           Optional[str]       = Field(None, max_length=300)
    email:         Optional[str]       = Field(None, max_length=254)
    interests:     Optional[List[str]] = Field(None, max_length=30)   # 관심 카테고리
    dietary:       Optional[List[str]] = Field(None, max_length=30)   # 식이 성향


class WithdrawRequest(BaseModel):
    """회원 탈퇴: 현재 비밀번호 확인 후 진행."""
    password: str = Field(..., min_length=1, max_length=64)
