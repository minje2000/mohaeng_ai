from fastapi import APIRouter
from app.schemas.nearby_schema import NearbyRequest, NearbyResponse
from app.services.nearby_service import generate_travel_course

router = APIRouter(prefix="/ai/nearby", tags=["nearby"])

@router.post("/course", response_model=NearbyResponse)
async def get_travel_course(req: NearbyRequest):
    """축제 주변 여행 코스 AI 생성"""
    return await generate_travel_course(req)
