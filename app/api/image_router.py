from fastapi import APIRouter
from fastapi.responses import JSONResponse

from app.schemas.image_schema import ImageGenerateRequest, ImageGenerateResponse
from app.services import image_service

router = APIRouter(prefix="/ai/image", tags=["AI 썸네일 생성"])

@router.post("/generate")
def generate_image(req: ImageGenerateRequest):
    try:
        image_base64 = image_service.generate_thumbnail(
            title=req.title,
            date_range=req.date_range,
            font_color=req.font_color,
            font_size=req.font_size,
            font_style=req.font_style,
            style_prompt=req.style_prompt,
        )
        return ImageGenerateResponse(image_base64=image_base64)
    except Exception as e:
        return JSONResponse(status_code=500, content={"error": str(e)})