import httpx
from app.core.config import settings


class GeminiService:
    def __init__(self):
        self.model = settings.GEMINI_MODEL or "gemini-2.5-flash"
        self.url = f"https://generativelanguage.googleapis.com/v1beta/models/{self.model}:generateContent"

    async def generate(self, history: list[dict], user_message: str, context: str = "") -> str:
        if not settings.GEMINI_API_KEY:
            return "안녕하세요. MOHAENG AI 챗봇입니다. Gemini API 키가 아직 설정되지 않았어요."

        system_prompt = (
            "너는 행사 플랫폼 MOHAENG의 AI 챗봇이다.\n"
            "자연스럽고 친절한 한국어로 답한다.\n"
            "너무 장황하지 않게, 실제 서비스 상담 챗봇처럼 답한다.\n"
            "행사 추천, 일정, 환불 규정, 문의, 지도, 달력 관련 질문에 강하다.\n"
            "모르면 모른다고 말한다."
        )

        parts = [{"text": f"[시스템 지침]\n{system_prompt}\n\n[참고 컨텍스트]\n{context}"}]

        for item in history[-6:]:
            role = item.get("role", "user")
            text = item.get("text", "")
            if not text:
                continue
            parts.append({"text": f"{'사용자' if role == 'user' else '상담사'}: {text}"})

        parts.append({"text": f"사용자: {user_message}"})

        payload = {
            "contents": [
                {
                    "parts": parts
                }
            ]
        }

        try:
            async with httpx.AsyncClient(timeout=settings.GEMINI_TIMEOUT_SECONDS) as client:
                res = await client.post(
                    self.url,
                    headers={
                        "x-goog-api-key": settings.GEMINI_API_KEY,
                        "Content-Type": "application/json",
                    },
                    json=payload,
                )

            if res.status_code >= 400:
                print("[Gemini ERROR]", res.status_code, res.text)
                return "지금은 자연 대화 응답을 생성하지 못했어요. 잠시 후 다시 시도해 주세요."

            data = res.json()
            return (
                data.get("candidates", [{}])[0]
                .get("content", {})
                .get("parts", [{}])[0]
                .get("text", "")
                .strip()
            ) or "지금은 자연 대화 응답을 생성하지 못했어요. 잠시 후 다시 시도해 주세요."

        except Exception as e:
            print("[Gemini EXCEPTION]", repr(e))
            return "지금은 자연 대화 응답을 생성하지 못했어요. 잠시 후 다시 시도해 주세요."