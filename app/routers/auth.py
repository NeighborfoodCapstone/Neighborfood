from pydantic import BaseModel, Field


class AuthRequest(BaseModel):
    phone_number: str = Field(
        ...,
        pattern=r'^010-\d{4}-\d{4}$',
        description="010-XXXX-XXXX 형식",
    )


class VerifyRequest(BaseModel):
    phone_number: str
    code: str = Field(..., min_length=6, max_length=6)
