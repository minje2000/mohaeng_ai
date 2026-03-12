from pydantic import BaseModel
from typing import Optional

class NearbyRequest(BaseModel):
    festival_name: str
    latitude: float
    longitude: float
    companion: str = "연인"                  # "연인" | "가족" | "혼자"
    transport: str = "자가용"                # "자가용" | "도보"
    festival_start_time: Optional[str] = None  # ex) "10:00"
    festival_end_time:   Optional[str] = None  # ex) "18:00"
    festival_date: Optional[str] = None        # ex) "2025-04-15" (행사 시작일)

class CourseItem(BaseModel):
    time: str
    place_name: str
    category: str                            # "축제" | "맛집" | "카페" | "관광"
    description: str
    tip: Optional[str] = None
    address: Optional[str] = None
    lat: Optional[float] = None
    lng: Optional[float] = None
    kakao_url: Optional[str] = None

class NearbyResponse(BaseModel):
    summary: str
    companion: str
    course: list[CourseItem]
