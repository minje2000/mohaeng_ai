import ast
import json
import re
from typing import Any, Dict, Optional

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
        )

    def evaluate_event(
        self, req: EventModerationRequest
    ) -> EventModerationResponse:
        messages = self._build_messages(req)
        raw_text = self._chat_generate(messages)

        print("===== RAW WATSONX CHAT RESPONSE START =====")
        print(raw_text)
        print("===== RAW WATSONX CHAT RESPONSE END =====")

        parsed = self._parse_json(raw_text)
        print("PARSED RESULT:", parsed)

        risk_score = self._clamp_float(parsed.get("risk_score", 1.0), default=1.0)
        reasons = parsed.get("reasons", [])
        summary = parsed.get("summary", "")

        if not isinstance(reasons, list):
            reasons = [str(reasons)]

        reasons = [str(x) for x in reasons][:3]
        summary = str(summary)

        if not reasons:
            reasons = ["판단 근거 부족"]

        if not summary:
            summary = "행사 검수 결과"

        return EventModerationResponse(
            risk_score=round(risk_score, 2),
            reasons=reasons,
            summary=summary,
        )

    def _build_messages(self, req: EventModerationRequest) -> list[dict]:
        payload = {
            "title": req.title or "",
            "simple_explain": req.simple_explain or "",
            "description": req.description or "",
            "lot_number_adr": req.lot_number_adr or "",
            "detail_adr": req.detail_adr or "",
            "topic_ids": req.topic_ids or "",
            "hashtag_ids": req.hashtag_ids or "",
        }

        system_prompt = """
너는 행사 등록 내용을 심사하는 위험도 검수 AI다.

목표:
- 행사 내용이 안전한 일반 행사인지
- 관리자 검토가 필요한 위험 가능성이 있는 행사인지
판단해서 위험 점수를 산출한다.

절대 규칙:
1. 반드시 JSON 객체만 반환하라.
2. 코드블록, 설명문, 인사말, 추가 문장을 절대 출력하지 마라.
3. 입력에 없는 사실을 추측하거나 지어내지 마라.
4. 정보가 부족하거나 의미가 모호하면 보수적으로 판단하라.
5. 정상 행사라도 위험 근거가 없으면 낮은 점수를 줘라.
6. 위험 여부가 애매하면 중간 이상 점수로 올려 관리자 검토가 가능하게 하라.

출력 형식:
{
  "risk_score": 0.00,
  "reasons": ["사유1", "사유2"],
  "summary": "한 줄 요약"
}

출력 규칙:
- risk_score는 0.00 이상 1.00 이하 숫자
- reasons는 최대 3개
- summary는 한 줄 한국어
- reasons는 실제 입력 내용에 근거해야 함

판단 기준:

[낮은 위험: 0.00 ~ 0.29]
- 교육, 전시, 공공, 문화, 체험, 설명회, 박람회, 멘토링 등 일반 행사
- 장소, 대상, 목적이 비교적 명확함
- 불법성, 사기성, 선정성, 과장성 단서가 없음

[중간 위험: 0.30 ~ 0.59]
- 정보가 부족함
- 제목은 정상처럼 보이지만 실제 내용이 불명확함
- 과도한 홍보성 문구, 외부 문의 유도, 목적 불명확
- 안전/정상 여부를 확신하기 어려움

[높은 위험: 0.60 ~ 1.00]
- 불법, 사기, 도박, 선정성, 성인 유흥, 폭력, 혐오, 허위과장, 금전 유도 가능성
- 외부 계좌 입금, 오픈채팅 유도, 비공개 링크 유도
- 행사 목적보다 판매/유인/유해성이 강함

중요:
- topic_ids, hashtag_ids는 숫자 또는 내부 식별자일 수 있으므로 의미를 모르면 과대해석하지 마라.
- title, simple_explain, description의 실제 문맥을 가장 중요하게 보라.
- lot_number_adr, detail_adr가 있으면 공개 행사 가능성을 높이는 참고 요소로만 사용하라.
""".strip()

        user_prompt = f"""
아래 행사 정보를 검수하라.

예시 1
입력:
{{
  "title": "청소년 진로 멘토링",
  "simple_explain": "고등학생 대상 무료 멘토링",
  "description": "대학생 멘토가 진로 상담과 학과 소개를 진행합니다.",
  "lot_number_adr": "서울시 강남구 ...",
  "detail_adr": "청소년센터 3층 강의실",
  "topic_ids": "",
  "hashtag_ids": ""
}}
출력:
{{
  "risk_score": 0.06,
  "reasons": ["교육 목적 행사", "행사 대상과 내용이 명확함", "유해 요소가 보이지 않음"],
  "summary": "정상적인 청소년 교육 행사"
}}

예시 2
입력:
{{
  "title": "주말 플리마켓 셀러 모집",
  "simple_explain": "지역 창작자와 주민이 함께하는 마켓",
  "description": "주민센터 앞 광장에서 열리는 지역 플리마켓 행사입니다.",
  "lot_number_adr": "서울시 강동구 ...",
  "detail_adr": "",
  "topic_ids": "",
  "hashtag_ids": ""
}}
출력:
{{
  "risk_score": 0.14,
  "reasons": ["일반적인 지역 행사", "장소와 행사 목적이 비교적 명확함"],
  "summary": "정상적인 지역 문화 행사"
}}

예시 3
입력:
{{
  "title": "대박 수익 특강",
  "simple_explain": "누구나 쉽게 돈 버는 방법 공개",
  "description": "선착순 비공개 링크 제공, 입금 후 참여 가능",
  "lot_number_adr": "",
  "detail_adr": "",
  "topic_ids": "",
  "hashtag_ids": ""
}}
출력:
{{
  "risk_score": 0.86,
  "reasons": ["금전 유도 표현이 있음", "비공개 링크와 입금 유도가 있음", "사기성 또는 허위과장 가능성이 있음"],
  "summary": "관리자 검토가 필요한 고위험 행사"
}}

예시 4
입력:
{{
  "title": "오늘 밤 프라이빗 파티",
  "simple_explain": "성인만 입장 가능",
  "description": "자세한 내용은 오픈채팅 문의",
  "lot_number_adr": "",
  "detail_adr": "",
  "topic_ids": "",
  "hashtag_ids": ""
}}
출력:
{{
  "risk_score": 0.82,
  "reasons": ["성인 대상 표현이 있음", "행사 정보가 부족함", "외부 문의 유도가 있음"],
  "summary": "관리자 검토가 필요한 행사"
}}

예시 5
입력:
{{
  "title": "특별한 모임",
  "simple_explain": "",
  "description": "관심 있는 분만 문의 주세요",
  "lot_number_adr": "",
  "detail_adr": "",
  "topic_ids": "",
  "hashtag_ids": ""
}}
출력:
{{
  "risk_score": 0.48,
  "reasons": ["행사 목적과 내용이 불명확함", "정보가 부족하여 안전성을 확신하기 어려움"],
  "summary": "정보 부족으로 검토가 필요한 행사"
}}

이제 아래 실제 입력을 검수하라.

실제 입력:
{json.dumps(payload, ensure_ascii=False)}

반드시 JSON 객체만 반환하라.
""".strip()

        return [
            {"role": "system", "content": system_prompt},
            {
                "role": "user",
                "content": [
                    {
                        "type": "text",
                        "text": user_prompt,
                    }
                ],
            },
        ]

    def _chat_generate(self, messages: list[dict]) -> str:
        try:
            result = self.model.chat(
                messages=messages,
                params={
                    "max_tokens": 260,
                    "time_limit": 10000,
                },
            )
        except Exception as e:
            print("WATSONX CHAT ERROR:", repr(e))
            return ""

        print("WATSONX CHAT RESULT TYPE:", type(result))
        try:
            print(
                "FULL CHAT RESULT =",
                json.dumps(result, ensure_ascii=False, indent=2, default=str),
            )
        except Exception:
            print("FULL CHAT RESULT REPR =", repr(result))

        if not isinstance(result, dict):
            return str(result).strip() if result is not None else ""

        choices = result.get("choices", [])
        if isinstance(choices, list) and choices:
            first = choices[0] if isinstance(choices[0], dict) else {}

            finish_reason = first.get("finish_reason")
            message = first.get("message", {})
            content = ""

            print("FINISH REASON =", finish_reason)
            print("USAGE =", result.get("usage"))

            if isinstance(message, dict):
                content = self._extract_chat_content(message.get("content"))

            print("CHAT CONTENT =", repr(content))
            if content:
                return content.strip()

        if "message" in result:
            message = result.get("message", {})
            if isinstance(message, dict):
                content = self._extract_chat_content(message.get("content"))
                print("TOP-LEVEL MESSAGE CONTENT =", repr(content))
                if content:
                    return content.strip()

        if isinstance(result, list) and result:
            first = result[0]
            if isinstance(first, dict):
                message = first.get("message", {})
                if isinstance(message, dict):
                    content = self._extract_chat_content(message.get("content"))
                    print("LIST FALLBACK CONTENT =", repr(content))
                    if content:
                        return content.strip()

        return ""

    def _extract_chat_content(self, content: Any) -> str:
        if content is None:
            return ""

        if isinstance(content, str):
            return content.strip()

        if isinstance(content, list):
            parts = []
            for item in content:
                if isinstance(item, dict):
                    text_value = item.get("text")
                    if text_value:
                        parts.append(str(text_value))
                elif isinstance(item, str):
                    parts.append(item)

            return "\n".join(parts).strip()

        return str(content).strip()

    def _parse_json(self, text: str) -> Dict[str, Any]:
        text = (text or "").strip()

        if not text:
            print("JSON PARSE ERROR: empty response")
            return {
                "risk_score": 1.0,
                "reasons": ["AI 응답 비어있음"],
                "summary": "빈 응답으로 관리자 검토 필요",
            }

        print("RAW BEFORE CLEAN:", repr(text))
        cleaned = self._extract_json_candidate(text)
        print("RAW AFTER CLEAN:", repr(cleaned))

        data = self._try_parse_standard_json(cleaned)
        if data is not None:
            return self._normalize_result(data)

        data = self._try_parse_relaxed_json(cleaned)
        if data is not None:
            return self._normalize_result(data)

        data = self._try_parse_python_dict(cleaned)
        if data is not None:
            return self._normalize_result(data)

        print("FAILED TEXT:", cleaned)
        return {
            "risk_score": 1.0,
            "reasons": ["AI 응답 파싱 실패"],
            "summary": "파싱 실패로 관리자 검토 필요",
        }

    def _extract_json_candidate(self, text: str) -> str:
        text = re.sub(r"```json", "", text, flags=re.IGNORECASE)
        text = re.sub(r"```", "", text)

        start = text.find("{")
        end = text.rfind("}")
        if start != -1 and end != -1 and end > start:
            text = text[start:end + 1]

        return text.strip()

    def _try_parse_standard_json(self, text: str) -> Optional[Dict[str, Any]]:
        try:
            data = json.loads(text)
            return data if isinstance(data, dict) else None
        except Exception as e:
            print("JSON LOADS ERROR:", e)
            return None

    def _try_parse_relaxed_json(self, text: str) -> Optional[Dict[str, Any]]:
        try:
            fixed = text
            fixed = fixed.replace("True", "true")
            fixed = fixed.replace("False", "false")
            fixed = fixed.replace("None", "null")
            fixed = re.sub(r",\s*}", "}", fixed)
            fixed = re.sub(r",\s*]", "]", fixed)

            data = json.loads(fixed)
            return data if isinstance(data, dict) else None
        except Exception as e:
            print("RELAXED JSON LOADS ERROR:", e)
            return None

    def _try_parse_python_dict(self, text: str) -> Optional[Dict[str, Any]]:
        try:
            data = ast.literal_eval(text)
            return data if isinstance(data, dict) else None
        except Exception as e:
            print("AST PARSE ERROR:", e)
            return None

    def _normalize_result(self, data: Dict[str, Any]) -> Dict[str, Any]:
        if "risk_score" not in data:
            if "riskScore" in data:
                data["risk_score"] = data["riskScore"]
            elif "score" in data:
                data["risk_score"] = data["score"]

        data.setdefault("risk_score", 1.0)
        data.setdefault("reasons", [])
        data.setdefault("summary", "")

        return data

    @staticmethod
    def _clamp_float(value: Any, default: float = 0.0) -> float:
        try:
            number = float(value)
        except (TypeError, ValueError):
            number = default

        if number < 0:
            return 0.0
        if number > 1:
            return 1.0
        return number