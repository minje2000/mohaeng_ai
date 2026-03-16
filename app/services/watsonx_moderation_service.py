import json
import re
from typing import Any, Dict

from ibm_watsonx_ai import Credentials
from ibm_watsonx_ai.foundation_models import ModelInference

from app.core.config import settings
from app.schemas.moderation_schema import (
    EventModerationRequest,
    EventModerationResponse,
)


class WatsonxModerationService:
    def __init__(self) -> None:
        print("API KEY EXISTS:", bool(settings.WATSONX_API_KEY))
        print("PROJECT ID:", settings.WATSONX_PROJECT_ID)
        print("URL:", settings.WATSONX_URL)
        print("MODEL:", settings.WATSONX_MODEL_ID)

        credentials = Credentials(
            api_key=settings.WATSONX_API_KEY.strip(),
            url=settings.WATSONX_URL.strip(),
        )

        self.model = ModelInference(
            model_id=settings.WATSONX_MODEL_ID.strip(),
            credentials=credentials,
            project_id=settings.WATSONX_PROJECT_ID.strip(),
            params={
                "temperature": 0,
                "max_new_tokens": 200,
                "min_new_tokens": 20,
            },
        )

    def evaluate_event(
        self, req: EventModerationRequest
    ) -> EventModerationResponse:
        prompt = self._build_prompt(req)
        raw_text = self._generate(prompt)

        print("===== RAW WATSONX RESPONSE START =====")
        print(raw_text)
        print("===== RAW WATSONX RESPONSE END =====")

        parsed = self._parse_json(raw_text)
        print("PARSED RESULT:", parsed)

        risk_score = float(parsed.get("risk_score", 0.00))
        reasons = parsed.get("reasons", [])
        summary = parsed.get("summary", "")

        if not isinstance(reasons, list):
            reasons = [str(reasons)]

        # 안전 보정
        if risk_score < 0:
            risk_score = 0.00
        if risk_score > 1:
            risk_score = 1.00

        return EventModerationResponse(
            risk_score=round(risk_score, 2),
            reasons=[str(x) for x in reasons],
            summary=str(summary),
        )

    def _build_prompt(self, req: EventModerationRequest) -> str:
        payload = {
            "title": req.title,
            "simple_explain": req.simple_explain,
            "description": req.description,
            "lot_number_adr": req.lot_number_adr,
            "detail_adr": req.detail_adr,
            "topic_ids": req.topic_ids,
            "hashtag_ids": req.hashtag_ids,
        }

        return f"""
너는 행사 등록 내용의 위험도를 판단하는 AI 검수 시스템이다.

반드시 JSON 객체만 반환하라.
절대로 설명 문장, 인사말, 코드블록, 마크다운, 추가 텍스트를 포함하지 마라.
반드시 아래 키 이름 그대로만 사용하라.

출력 형식:
{{
  "risk_score": 0.00,
  "reasons": ["사유1", "사유2"],
  "summary": "한 줄 요약"
}}

판단 기준:
- 불법/사기/도박/선정성/과도한 광고성/허위과장/금전유도 가능성
- risk_score는 0.00 이상 1.00 이하 숫자
- 정상적인 공공행사, 교육행사, 문화행사는 낮은 점수
- 관리자 검토가 필요할수록 높은 점수

입력 데이터:
{json.dumps(payload, ensure_ascii=False)}

반드시 JSON만 반환하라.
""".strip()

    def _generate(self, prompt: str) -> str:
        result = self.model.generate_text(prompt=prompt)

        print("WATSONX RESULT TYPE:", type(result))
        print("WATSONX RESULT REPR:", repr(result))

        if isinstance(result, str):
            return result

        if isinstance(result, dict):
            # 1순위: results[0].generated_text
            results = result.get("results")
            if isinstance(results, list) and results:
                first = results[0]
                print("WATSONX FIRST RESULT:", first)

                if isinstance(first, dict):
                    generated_text = first.get("generated_text")
                    if generated_text:
                        return str(generated_text)

                    # 혹시 다른 키에 텍스트가 있으면 보정
                    for key in ["text", "output", "content"]:
                        if first.get(key):
                            return str(first.get(key))

            # 2순위: 최상위 다른 키들 확인
            for key in ["generated_text", "text", "output", "content"]:
                if result.get(key):
                    return str(result.get(key))

        return ""

    def _parse_json(self, text: str) -> Dict[str, Any]:
        text = text.strip()

        # ```json ... ``` 제거
        text = re.sub(r"^```json\s*", "", text)
        text = re.sub(r"^```\s*", "", text)
        text = re.sub(r"\s*```$", "", text)

        # JSON 본문만 추출
        start = text.find("{")
        end = text.rfind("}")
        if start != -1 and end != -1 and end > start:
            text = text[start:end + 1]

        try:
            data = json.loads(text)

            # 키 이름이 다르게 올 경우 보정
            if "risk_score" not in data:
                if "riskScore" in data:
                    data["risk_score"] = data["riskScore"]
                elif "score" in data:
                    data["risk_score"] = data["score"]

            if "reasons" not in data:
                data["reasons"] = []

            if "summary" not in data:
                data["summary"] = ""

            return data

        except Exception as e:
            print("JSON PARSE ERROR:", e)
            print("FAILED TEXT:", text)

            return {
                "risk_score": -1,
                "reasons": ["AI 응답 파싱 실패"],
                "summary": "파싱 실패",
            }