from pydantic import BaseModel, Field


class RegisterRequest(BaseModel):
    """회원가입: ID·비밀번호·휴대폰 번호로 가입합니다."""
    login_id:     str = Field(..., min_length=3, max_length=30,
                              pattern=r"^[a-zA-Z0-9_]+$",
                              description="영문·숫자·언더스코어 3~30자")
    password:     str = Field(..., min_length=6, max_length=64,
                              description="6~64자 비밀번호")
    phone_number: str = Field(..., description="휴대폰 번호 (예: 010-1234-5678)")
    nickname:     str | None = Field(None, min_length=1, max_length=20)


class LoginRequest(BaseModel):
    """로그인: ID·비밀번호."""
    login_id: str = Field(..., min_length=1, max_length=30)
    password: str = Field(..., min_length=1, max_length=64)


class AuthRequest(BaseModel):
    """비밀번호 재설정 OTP 요청: 가입 시 등록한 휴대폰 번호."""
    phone_number: str = Field(..., description="가입 시 등록한 휴대폰 번호")


class PasswordResetRequest(BaseModel):
    """비밀번호 재설정: OTP 코드 + 새 비밀번호."""
    phone_number: str = Field(..., description="가입 시 등록한 휴대폰 번호")
    code:         str = Field(..., min_length=6, max_length=6, description="6자리 OTP")
    new_password: str = Field(..., min_length=6, max_length=64)


class VerifyRequest(BaseModel):
    """(호환용) OTP 검증 요청 — 비밀번호 재설정 흐름에서 사용."""
    phone_number: str
    code:         str
