import os
import base64
from io import BytesIO
from PIL import ImageFont, ImageDraw, Image
from dotenv import load_dotenv
from openai import OpenAI

load_dotenv(dotenv_path=os.path.join(os.path.dirname(__file__), '../../.env'))
client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

# ── 폰트 매핑 ──────────────────────────────────────────────
FONT_MAP = {
    "malgun":  "C:/Windows/Fonts/malgun.ttf",    # 맑은 고딕 (기본)
    "bold":    "C:/Windows/Fonts/malgunbd.ttf",  # 맑은 고딕 Bold
    "myungjo": "C:/Windows/Fonts/batang.ttc",    # 바탕 (명조)
    "gothic":  "C:/Windows/Fonts/gulim.ttc",     # 굴림
}

def _hex_to_rgba(hex_color: str, alpha: int = 255):
    """HEX 색상 코드를 RGBA 튜플로 변환합니다."""
    hex_color = hex_color.lstrip("#")
    r, g, b = tuple(int(hex_color[i:i+2], 16) for i in (0, 2, 4))
    return (r, g, b, alpha)

def _add_korean_text(
    image_b64: str,
    title: str,
    date_range: str,
    font_color: str = "#FFFFFF",
    font_size: int = 72,
    font_style: str = "malgun"
) -> str:
    """생성된 이미지에 한글 제목과 날짜를 직접 렌더링합니다."""
    img_bytes = base64.b64decode(image_b64)
    img = Image.open(BytesIO(img_bytes)).convert("RGBA")
    draw = ImageDraw.Draw(img)

    W, H = img.size  # 1024x1024

    font_path = FONT_MAP.get(font_style, FONT_MAP["malgun"])
    color = _hex_to_rgba(font_color)
    shadow = (0, 0, 0, 160)

    # ── 제목 (상단 7% 지점)
    font_title = ImageFont.truetype(font_path, size=font_size)
    bbox = draw.textbbox((0, 0), title, font=font_title)
    tw = bbox[2] - bbox[0]
    tx = (W - tw) / 2
    ty = H * 0.07
    draw.text((tx + 3, ty + 3), title, font=font_title, fill=shadow)
    draw.text((tx, ty), title, font=font_title, fill=color)

    # ── 날짜 (하단 88% 지점, 제목 크기의 절반)
    font_date = ImageFont.truetype(font_path, size=font_size // 2)
    bbox2 = draw.textbbox((0, 0), date_range, font=font_date)
    dw = bbox2[2] - bbox2[0]
    dx = (W - dw) / 2
    dy = H * 0.88
    draw.text((dx + 2, dy + 2), date_range, font=font_date, fill=shadow)
    draw.text((dx, dy), date_range, font=font_date, fill=color)

    # ── base64로 다시 인코딩
    output = BytesIO()
    img.convert("RGB").save(output, format="PNG")
    return base64.b64encode(output.getvalue()).decode()


def generate_thumbnail(title, date_range, font_color="#FFFFFF", font_size=72, font_style="malgun", style_prompt=None):

    style_hint = f'- Additional style/mood from user: "{style_prompt}"' if style_prompt else ""

    system_prompt = f"""
You are a professional Korean festival poster illustrator.
Create a DALL-E 3 prompt for a high-quality flat illustration poster background.

[Event]
- Title: "{title}"
- Date: "{date_range}"
{style_hint}

[Style Reference — Korean Festival Poster]
- Rich, detailed flat 2D illustration (similar to professional Korean cultural festival posters)
- The ENTIRE background must be filled with thematic illustrations related to the event title
- Include small cute characters (사람들) actively enjoying the festival scene
- Strong seasonal and thematic color palette — infer season and mood from the title
- Layered composition: foreground elements, mid-ground scene, background sky/landscape
- Decorative motifs directly tied to the event theme (e.g. cherry blossoms for spring festival, lanterns for night festival, ornaments for Christmas)
- Warm, vibrant, inviting atmosphere — feels like a real professional Korean public event poster
- Square 1:1 composition, center-focused
- Leave top 15% and bottom 15% as slightly less busy areas for text overlay
- NO text, NO letters, NO numbers anywhere in the image

Output ONLY the English DALL-E 3 prompt. Be specific and detailed (150+ words).
"""

    try:
        # 1. GPT로 프롬프트 고도화
        gpt_response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[{"role": "user", "content": system_prompt}]
        )
        final_prompt = gpt_response.choices[0].message.content.strip()
        print(f"[DALL-E 3 프롬프트]: {final_prompt}")

        # 2. DALL-E 3 호출
        image_response = client.images.generate(
            model="dall-e-3",
            prompt=final_prompt,
            size="1024x1024",
            quality="standard",
            n=1,
            response_format="b64_json"
        )
        raw_b64 = image_response.data[0].b64_json
        return raw_b64

    except Exception as e:
        print(f"이미지 생성 실패: {e}")
        raise e
