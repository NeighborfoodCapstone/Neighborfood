from pydantic import BaseModel
from typing   import Optional


class QrIssueRequest(BaseModel):
    subjectId:  str
    purpose:    str = "pickup_confirm"
    ttlSeconds: int = 300


class QrVerifyRequest(BaseModel):
    token:    Optional[str] = None
    rawValue: Optional[str] = None
