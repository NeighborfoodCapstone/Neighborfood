# -*- coding: utf-8 -*-
from __future__ import annotations

from typing import Optional

from pydantic import BaseModel


class DummyTargetRequest(BaseModel):
    lat: float
    lng: float
    accuracy: Optional[float] = None
    address: Optional[str] = None
    radiusM: float = 300
    subjectId: Optional[str] = None


class GpsCheckRequest(BaseModel):
    lat: float
    lng: float
    accuracy: Optional[float] = None
    radiusM: float = 300
    accuracyLimitM: float = 1500


class QrIssuedRequest(BaseModel):
    qrSessionId: Optional[str] = None