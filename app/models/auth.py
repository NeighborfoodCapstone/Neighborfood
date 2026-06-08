from pydantic import BaseModel, Field


class AuthRequest(BaseModel):
    phone_number: str = Field(..., min_length=10, max_length=20)


class VerifyRequest(BaseModel):
    phone_number: str = Field(..., min_length=10, max_length=20)
    code: str = Field(..., min_length=4, max_length=10)
