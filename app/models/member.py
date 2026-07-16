from pydantic import BaseModel, Field


class ChatOpen(BaseModel):
    """채팅방 열기: 게시글 ID를 받아 작성자와의 1:1 방을 만들거나 기존 방을 반환."""
    post_id: int


class MessageSend(BaseModel):
    """채팅 메시지 전송."""
    content: str = Field(..., min_length=1, max_length=1000)


class NeighborhoodVerify(BaseModel):
    """동네(위치) 인증: 프런트에서 현재 위치 좌표와 동네 이름을 전달."""
    neighborhood: str = Field(..., min_length=1, max_length=60)
    lat: float
    lng: float


class TransactionCreate(BaseModel):
    """거래 생성: 게시글에 대해 신청자(나)가 수령자가 되는 거래를 만듭니다."""
    post_id: int
    appointment_at: str | None = None   # ISO 일시(선택)


class TransactionUpdate(BaseModel):
    """거래 상태 전환: pending → confirmed → completed / canceled."""
    status: str = Field(..., pattern=r"^(pending|confirmed|completed|canceled)$")
    appointment_at: str | None = None
