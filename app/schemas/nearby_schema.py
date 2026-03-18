from pydantic import BaseModel
from typing import Optional

class NearbyRequest(BaseModel):
    festival_name: str
    latitude: float
    longitude: float
    companion: str = "연인"
    transport: str = "자가용"
    festival_start_time: Optional[str] = None
    festival_end_time:   Optional[str] = None
    festival_date: Optional[str] = None
    festival_address: Optional[str] = None  # ← 추가

class CourseItem(BaseModel):
    time: str
    place_name: str
    category: str
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