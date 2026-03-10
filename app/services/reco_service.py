import json
import math
import re
from sentence_transformers import SentenceTransformer
from transformers import pipeline
from PIL import Image
import io

# ── 모델 로딩 (서버 시작 시 1회만 로드) ──────────────────────
print("AI 모델 로딩 중...")

# 한국어 특화 임베딩 모델
embedding_model = SentenceTransformer("jhgan/ko-sroberta-multitask")

# 텍스트 생성 모델 (태그 추천용)
text_generator = pipeline(
    "text2text-generation",
    model="google/flan-t5-base",
    max_new_tokens=300
)

# 이미지 캡셔닝 모델 (썸네일 분석용)
image_captioner = pipeline(
    "image-to-text",
    model="Salesforce/blip-image-captioning-base"
)

print("AI 모델 로딩 완료!")

# ── 카테고리 / 주제 목록 ───────────────────────────────────────
CATEGORY_LIST = (
    "1:컨퍼런스, 2:박람회, 3:전시, 4:강연/세미나, 5:교육/워크숍, "
    "6:공연/콘서트, 7:페스티벌/축제, 8:취업/채용, 9:네트워킹/파티, "
    "10:경진대회, 11:플리마켓/장터, 12:토크콘서트, 13:스포츠/레저, "
    "14:원데이 클래스, 15:팝업스토어"
)

TOPIC_LIST = (
    "1:IT, 2:비즈니스창업, 3:마케팅브랜딩, 4:디자인아트, 5:재테크투자, 6:취업이직, "
    "7:자기계발, 8:인문사회과학, 9:환경ESG, 10:건강스포츠, 11:요리베이킹, 12:음료주류, "
    "13:여행아웃도어, 14:인테리어리빙, 15:패션뷰티, 16:반려동물, 17:음악공연, "
    "18:영화만화게임, 19:사진영상제작, 20:핸드메이드공예, 21:육아교육, "
    "22:심리명상, 23:연애결혼, 24:종교, 25:기타"
)


# ── 임베딩 ────────────────────────────────────────────────────
def get_embedding(text: str) -> list[float]:
    """텍스트 → 임베딩 벡터 (한국어 특화)"""
    if len(text) > 512:
        text = text[:512]
    vector = embedding_model.encode(text)
    return vector.tolist()


# ── 코사인 유사도 ──────────────────────────────────────────────
def cosine_similarity(v1: list, v2: list) -> float:
    dot = sum(a * b for a, b in zip(v1, v2))
    norm1 = math.sqrt(sum(a ** 2 for a in v1))
    norm2 = math.sqrt(sum(b ** 2 for b in v2))
    if norm1 == 0 or norm2 == 0:
        return 0.0
    return dot / (norm1 * norm2)


# ── 추천 ──────────────────────────────────────────────────────
def recommend_events(user_text: str, events: list[dict]) -> list[int]:
    """유사도 계산 후 상위 6개 event_id 반환"""
    user_vector = get_embedding(user_text)

    scored = []
    for event in events:
        try:
            event_vector = json.loads(event["embedding"])
            score = cosine_similarity(user_vector, event_vector)
            scored.append({"event_id": event["event_id"], "score": score})
        except Exception:
            continue

    scored.sort(key=lambda x: x["score"], reverse=True)
    return [item["event_id"] for item in scored[:6]]


# ── 태그 추천 ──────────────────────────────────────────────────
def suggest_tags(title: str, simple_explain: str, image_bytes: bytes | None) -> dict:
    """
    텍스트 + 이미지 분석 → 카테고리/주제/해시태그 추천
    반환: {"categoryId": 1, "topicIds": [1, 11], "hashtagNames": ["AI", "개발자"]}
    """
    # 이미지 캡션 추출
    image_caption = ""
    if image_bytes:
        try:
            image = Image.open(io.BytesIO(image_bytes)).convert("RGB")
            result = image_captioner(image)
            image_caption = result[0]["generated_text"] if result else ""
        except Exception:
            image_caption = ""

    image_hint = f"\n이미지 설명: {image_caption}" if image_caption else ""

    prompt = f"""다음 행사 정보를 분석하여 카테고리ID, 주제ID 목록, 해시태그를 추천해줘.

행사 제목: {title}
한줄 설명: {simple_explain}{image_hint}

카테고리 목록 (하나만 선택): {CATEGORY_LIST}
주제 목록 (최대 3개 선택): {TOPIC_LIST}

반드시 아래 JSON 형식으로만 응답해. 다른 말은 하지 마.
{{"categoryId": 숫자, "topicIds": [숫자, 숫자], "hashtagNames": ["태그1", "태그2", "태그3", "태그4", "태그5"]}}"""

    result = text_generator(prompt)
    raw_text = result[0]["generated_text"] if result else ""

    match = re.search(r'\{.*\}', raw_text, re.DOTALL)
    if match:
        try:
            return json.loads(match.group())
        except Exception:
            pass

    # 파싱 실패 시 기본값
    return {
        "categoryId": 1,
        "topicIds": [1],
        "hashtagNames": []
    }
