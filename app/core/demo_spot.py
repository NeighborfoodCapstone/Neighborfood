# -*- coding: utf-8 -*-
"""체험 거래(관리자 체험 모드) 공용 상수 — 약속 장소 고정값.

부스 체험 거래의 만남 장소는 서일대학교 호천관(서울 중랑구 용마산로90길 28)으로 고정합니다.
좌표는 환경변수 DEMO_SPOT_LAT / DEMO_SPOT_LNG 로 덮어쓸 수 있습니다.
(기본값은 근사 좌표이므로, 지도에서 확인한 값으로 바꿔 주세요.)
"""
import os

DEMO_PREFIX = "[체험] "

SPOT_ADDRESS = "서울 중랑구 용마산로90길 28 (서일대학교 호천관)"
SPOT_LAT = float(os.getenv("DEMO_SPOT_LAT", "37.5890"))
SPOT_LNG = float(os.getenv("DEMO_SPOT_LNG", "127.0940"))


def is_demo_title(title) -> bool:
    return str(title or "").startswith(DEMO_PREFIX)


def spot():
    """(주소, 위도, 경도)"""
    return SPOT_ADDRESS, SPOT_LAT, SPOT_LNG
