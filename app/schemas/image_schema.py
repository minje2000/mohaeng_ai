from pydantic import BaseModel
from typing import Optional

class ImageGenerateRequest(BaseModel):
    title: str
    date_range: str                          # 언더스코어
    font_color: Optional[str] = "#FFFFFF"
    font_size: Optional[int] = 72
    font_style: Optional[str] = "malgun"
    style_prompt: Optional[str] = None

class ImageGenerateResponse(BaseModel):
    image_base64: str
    format: str = "png"