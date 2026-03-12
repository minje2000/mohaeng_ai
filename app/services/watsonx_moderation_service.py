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
            api_key=settings.WATSONX_API_KEY,
            url=settings.WATSONX_URL,
        )

        self.model = ModelInference(
            model_id=settings.WATSONX_MODEL_ID,
            credentials=credentials,
            project_id=settings.WATSONX_PROJECT_ID,
            params={
                "temperature": 0,
                "max_new_tokens": 300,
            },
        )

    def evaluate_event(
        self, req: EventModerationRequest
    ) -> EventModerationResponse:
        prompt = self._build_prompt(req)
        raw_text = self._generate(prompt)
        parsed = self._parse_json(raw_text)

        risk_score = float(parsed.get("risk_score", 0.0))
        reasons = parsed.get("reasons", [])
        summary = parsed.get("summary", "")

        if not isinstance(reasons, list):
            reasons = [str(reasons)]

        # 안전 보정
        if risk_score < 0:
            risk_score = 0.0
        if risk_score > 1:
            risk_score = 1.0

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

반드시 아래 JSON 형식으로만 답변하라.
설명 문장, 코드블록, 마크다운 없이 JSON만 반환하라.

출력 형식:
{{
  "risk_score": 0.0,
  "reasons": ["사유1", "사유2"],
  "summary": "한 줄 요약"
}}

판단 기준:
- 불법/사기/도박/선정성/과도한 광고성/허위과장/금전유도 가능성
- risk_score는 0.0 이상 1.0 이하 숫자
- 정상적인 행사면 낮은 점수
- 관리자 검토가 필요할수록 높은 점수

입력 데이터:
{json.dumps(payload, ensure_ascii=False)}
""".strip()

    def _generate(self, prompt: str) -> str:
        result = self.model.generate_text(prompt=prompt)

        # SDK 응답 형태 대응
        if isinstance(result, str):
            return result

        if isinstance(result, dict):
            results = result.get("results")
            if isinstance(results, list) and results:
                first = results[0]
                if isinstance(first, dict):
                    return str(first.get("generated_text", ""))

        return ""

    def _parse_json(self, text: str) -> Dict[str, Any]:
        text = text.strip()

        # 혹시 ```json ... ``` 형태면 제거
        text = re.sub(r"^```json\s*", "", text)
        text = re.sub(r"^```\s*", "", text)
        text = re.sub(r"\s*```$", "", text)

        # JSON 본문만 추출 시도
        start = text.find("{")
        end = text.rfind("}")
        if start != -1 and end != -1 and end > start:
            text = text[start : end + 1]

        try:
            return json.loads(text)
        except Exception:
            # 파싱 실패 시 안전하게 높은 점수로 반환
            return {
                "risk_score": 0.8,
                "reasons": ["AI 응답 파싱 실패"],
                "summary": "관리자 검토 필요",
            }