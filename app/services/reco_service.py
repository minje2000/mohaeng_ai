from sentence_transformers import SentenceTransformer, util
import torch
import numpy as np
import os
from dotenv import load_dotenv
from openai import OpenAI

load_dotenv()

# ── 모델 로딩 및 API 설정 ──────────────────────────────────
embedding_model = SentenceTransformer('jhgan/ko-sroberta-multitask')
client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

# ── 카테고리 / 주제 / 해시태그 목록 ──────────────────────────
CATEGORIES = [
    {"id": 1,  "name": "컨퍼런스",      "desc": "컨퍼런스 학술대회 발표 포럼 심포지엄"},
    {"id": 2,  "name": "박람회",        "desc": "박람회 엑스포 전시 부스 산업"},
    {"id": 3,  "name": "전시",          "desc": "전시 갤러리 아트 작품 관람"},
    {"id": 4,  "name": "강연/세미나",   "desc": "강연 세미나 강의 스피치 발표 토론"},
    {"id": 5,  "name": "교육/워크숍",   "desc": "교육 워크숍 수업 실습 훈련 클래스"},
    {"id": 6,  "name": "공연/콘서트",   "desc": "공연 콘서트 음악 밴드 뮤지컬 연주 공연장"},
    {"id": 7,  "name": "페스티벌/축제", "desc": "페스티벌 축제 야외 불꽃 들불 봄 여름 겨울 문화 지역 행사"},
    {"id": 8,  "name": "취업/채용",     "desc": "취업 채용 구직 면접 이력서 잡페어"},
    {"id": 9,  "name": "네트워킹/파티", "desc": "네트워킹 파티 모임 친목 만남 교류"},
    {"id": 10, "name": "경진대회",      "desc": "경진대회 해커톤 공모전 경쟁 우승"},
    {"id": 11, "name": "플리마켓/장터", "desc": "플리마켓 장터 벼룩시장 마켓 판매 핸드메이드"},
    {"id": 12, "name": "토크콘서트",    "desc": "토크콘서트 강사 연사 이야기 대화"},
    {"id": 13, "name": "스포츠/레저",   "desc": "스포츠 레저 운동 야외 등산 캠핑 마라톤"},
    {"id": 14, "name": "원데이 클래스", "desc": "원데이클래스 체험 만들기 DIY 하루"},
    {"id": 15, "name": "팝업스토어",    "desc": "팝업스토어 브랜드 한정 오픈 쇼룸"},
]

TOPICS = [
    {"id": 1,  "name": "IT",            "desc": "IT 기술 소프트웨어 개발 프로그래밍 AI 인공지능 데이터"},
    {"id": 2,  "name": "비즈니스 창업", "desc": "비즈니스 창업 스타트업 사업 기업가"},
    {"id": 3,  "name": "마케팅 브랜딩", "desc": "마케팅 브랜딩 광고 홍보 SNS 콘텐츠"},
    {"id": 4,  "name": "디자인 아트",   "desc": "디자인 아트 예술 그래픽 UI 창작"},
    {"id": 5,  "name": "재테크 투자",   "desc": "재테크 투자 주식 부동산 금융 경제"},
    {"id": 6,  "name": "취업 이직",     "desc": "취업 이직 채용 커리어 직장 면접"},
    {"id": 7,  "name": "자기계발",      "desc": "자기계발 성장 독서 목표 동기 습관"},
    {"id": 8,  "name": "인문 사회 과학","desc": "인문 사회 과학 역사 철학 심리 학문"},
    {"id": 9,  "name": "환경 ESG",      "desc": "환경 ESG 지속가능 탄소 생태 녹색 자연"},
    {"id": 10, "name": "건강 스포츠",   "desc": "건강 스포츠 운동 피트니스 요가 웰니스"},
    {"id": 11, "name": "요리 베이킹",   "desc": "요리 베이킹 음식 쿠킹 레시피 푸드"},
    {"id": 12, "name": "음료 주류",     "desc": "음료 주류 커피 와인 맥주 칵테일 음주"},
    {"id": 13, "name": "여행 아웃도어", "desc": "여행 아웃도어 캠핑 등산 트레킹 자연 탐방 야외 축제"},
    {"id": 14, "name": "인테리어 리빙", "desc": "인테리어 리빙 홈 공간 가구 인테리어"},
    {"id": 15, "name": "패션 뷰티",     "desc": "패션 뷰티 스타일 의류 화장 메이크업"},
    {"id": 16, "name": "반려동물",      "desc": "반려동물 강아지 고양이 펫 동물"},
    {"id": 17, "name": "음악 공연",     "desc": "음악 공연 콘서트 밴드 악기 연주 노래"},
    {"id": 18, "name": "영화 만화 게임","desc": "영화 만화 게임 웹툰 애니메이션 유튜브"},
    {"id": 19, "name": "사진 영상제작", "desc": "사진 영상 촬영 카메라 영상제작 유튜버"},
    {"id": 20, "name": "핸드메이드 공예","desc": "핸드메이드 공예 DIY 만들기 바느질 도예"},
    {"id": 21, "name": "육아 교육",     "desc": "육아 교육 어린이 아이 부모 키즈 학습"},
    {"id": 22, "name": "심리 명상",     "desc": "심리 명상 마인드풀니스 치유 힐링 상담"},
    {"id": 23, "name": "연애 결혼",     "desc": "연애 결혼 데이트 웨딩 커플 소개팅"},
    {"id": 24, "name": "종교",          "desc": "종교 기독교 불교 천주교 신앙 예배"},
    {"id": 25, "name": "기타",          "desc": "기타 일반 다양 복합"},
]

HASHTAGS = [
    {"id": 1,  "name": "즐거운",        "desc": "즐거운 재미있는 신나는 유쾌한"},
    {"id": 2,  "name": "평온한",        "desc": "평온한 차분한 고요한 안정된"},
    {"id": 3,  "name": "열정적인",      "desc": "열정적인 뜨거운 패션 에너지"},
    {"id": 4,  "name": "디지털디톡스",  "desc": "디지털 디톡스 자연 오프라인 힐링"},
    {"id": 5,  "name": "창의적인",      "desc": "창의적인 독창적인 아이디어 혁신"},
    {"id": 6,  "name": "영감을주는",    "desc": "영감 인사이트 동기부여 감동"},
    {"id": 7,  "name": "활기찬",        "desc": "활기찬 에너지 역동 생동감 축제 야외"},
    {"id": 8,  "name": "편안한",        "desc": "편안한 릴랙스 쉬는 휴식 힐링"},
    {"id": 9,  "name": "트렌디한",      "desc": "트렌디 최신 유행 핫플 트렌드"},
    {"id": 10, "name": "전문적인",      "desc": "전문 전문가 고급 심화 직업"},
    {"id": 11, "name": "교육적인",      "desc": "교육 학습 배움 지식 성장"},
    {"id": 12, "name": "감성적인",      "desc": "감성 감동 예술 아름다운 서정적"},
    {"id": 13, "name": "도전적인",      "desc": "도전 경쟁 극복 목표 달성"},
    {"id": 14, "name": "따뜻한",        "desc": "따뜻한 온기 정 커뮤니티 나눔"},
    {"id": 15, "name": "유익한",        "desc": "유익 도움 실용 정보 알찬"},
    {"id": 16, "name": "색다른",        "desc": "색다른 특별 이색 독특 새로운"},
    {"id": 17, "name": "미니멀한",      "desc": "미니멀 심플 깔끔 정돈"},
    {"id": 18, "name": "역동적인",      "desc": "역동 활발 움직임 파워 에너지 스포츠"},
    {"id": 19, "name": "신선한",        "desc": "신선 새로운 참신 설레는 봄"},
    {"id": 20, "name": "친근한",        "desc": "친근 친절 편한 가벼운 일상"},
    {"id": 21, "name": "화려한",        "desc": "화려 강렬 컬러풀 볼거리 쇼"},
    {"id": 22, "name": "조용한",        "desc": "조용 고요 혼자 집중 내향"},
    {"id": 23, "name": "성장하는",      "desc": "성장 발전 커리어 자기계발 미래"},
    {"id": 24, "name": "함께하는",      "desc": "함께 협력 팀 공동체 소통 나눔"},
    {"id": 25, "name": "지속가능한",    "desc": "지속가능 환경 친환경 ESG 녹색"},
    {"id": 26, "name": "흥미진진한",    "desc": "흥미 재미 스릴 설레는 불꽃 축제"},
    {"id": 27, "name": "진지한",        "desc": "진지 심층 진중 토론 학술"},
    {"id": 28, "name": "자유로운",      "desc": "자유 개방 오픈 자유형 야외 캠핑"},
    {"id": 29, "name": "집중하는",      "desc": "집중 몰입 딥다이브 workshop"},
    {"id": 30, "name": "친환경적인",    "desc": "친환경 자연 녹색 에코 생태"},
]

# ── 임베딩 캐시 ───────────────────────────────────────────────
_cat_embeddings = None
_topic_embeddings = None
_hashtag_embeddings = None

def _get_cat_embeddings():
    global _cat_embeddings
    if _cat_embeddings is None:
        texts = [c["name"] + " " + c["desc"] for c in CATEGORIES]
        _cat_embeddings = embedding_model.encode(texts, convert_to_tensor=True)
    return _cat_embeddings

def _get_topic_embeddings():
    global _topic_embeddings
    if _topic_embeddings is None:
        texts = [t["name"] + " " + t["desc"] for t in TOPICS]
        _topic_embeddings = embedding_model.encode(texts, convert_to_tensor=True)
    return _topic_embeddings

def _get_hashtag_embeddings():
    global _hashtag_embeddings
    if _hashtag_embeddings is None:
        texts = [h["name"] + " " + h["desc"] for h in HASHTAGS]
        _hashtag_embeddings = embedding_model.encode(texts, convert_to_tensor=True)
    return _hashtag_embeddings

# ── 임베딩 (추천용) ───────────────────────────────────────────
def get_embedding(text: str) -> str:
    text = text[:512]
    vec = embedding_model.encode(text)
    return ",".join(map(str, vec.tolist()))

def cosine_similarity(v1, v2):
    a = np.array(v1)
    b = np.array(v2)
    return float(np.dot(a, b) / (np.linalg.norm(a) * np.linalg.norm(b) + 1e-9))

def recommend_events(user_text: str, events: list, user_region_ids: list = []) -> list:
    user_vec = [float(x) for x in get_embedding(user_text).split(",")]

    region_pref = {}
    for rid in user_region_ids:
        prefix = str(rid)[:2]
        region_pref[prefix] = region_pref.get(prefix, 0) + 1
    total = sum(region_pref.values()) or 1
    region_pref = {k: (v / total) * 0.3 for k, v in region_pref.items()}

    scored = []
    for e in events:
        try:
            embedding_str = e.embedding if hasattr(e, 'embedding') else e["embedding"]
            event_id = e.event_id if hasattr(e, 'event_id') else e["event_id"]
            region_id = e.region_id if hasattr(e, 'region_id') else e.get("region_id")

            embedding_str = embedding_str.strip().strip('"')
            ev = [float(x.strip().strip('"')) for x in embedding_str.split(",")]
            text_score = cosine_similarity(user_vec, ev)

            region_bonus = 0.0
            if region_id:
                prefix = str(region_id)[:2]
                region_bonus = region_pref.get(prefix, 0.0)

            final_score = 0.7 * text_score + region_bonus
            scored.append((final_score, event_id))
        except Exception as ex:
            continue

    scored.sort(reverse=True)
    return [int(eid) for _, eid in scored[:6]]


# ── 한줄 설명 생성 (GPT 연동) ──────────────────────────────────
def _make_simple_explain_with_llm(title: str, description: str, category_name: str) -> str:
    """GPT API를 사용하여 맥락에 맞는 감성적인 한 줄 요약을 생성합니다."""

    if not description or len(description.strip()) < 5:
        return f"{title}에서 특별한 경험을 만나보세요."

    prompt = f"""
행사 카테고리: {category_name}
행사 제목: {title}
행사 상세설명: {description}

당신은 사람들의 마음을 끄는 전문 카피라이터입니다. 
위 내용을 바탕으로 이 행사를 홍보할 수 있는 '50자 이내의 감성적이고 매력적인 한 줄 요약'을 작성해주세요.
딱딱한 템플릿(예: ~을 주제로 한 ~에 초대합니다)은 절대 피하고, 시나 감성적인 광고 카피처럼 자연스럽고 멋지게 써주세요.

예시: "빛나는 별을 보며 너와 나누는 이야기."
출력: (다른 부연 설명 없이 오직 생성된 한 줄 카피만 출력할 것)
"""
    try:
        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[{"role": "user", "content": prompt}]
        )
        return response.choices[0].message.content.strip().replace('"', '').replace("'", "")
    except Exception as e:
        print(f"GPT API 호출 실패: {e}")
        return f"{title}에서 잊지 못할 시간을 만들어보세요."


# ── AI 태그 추천 ──────────────────────────────────────────────
def suggest_tags(title: str, simple_explain: str, image_bytes: bytes = None) -> dict:
    text = f"{title} {title} {simple_explain}"
    query_vec = embedding_model.encode(text, convert_to_tensor=True)

    # ── 카테고리
    cat_sims = util.cos_sim(query_vec, _get_cat_embeddings())[0]
    cat_idx = int(torch.argmax(cat_sims).item())
    category_id = CATEGORIES[cat_idx]["id"]
    category_name = CATEGORIES[cat_idx]["name"]

    # ── 주제
    TOPIC_THRESHOLD = 0.3
    topic_sims = util.cos_sim(query_vec, _get_topic_embeddings())[0]
    topic_scores = sorted(
        [(float(topic_sims[i].item()), TOPICS[i]) for i in range(len(TOPICS))],
        key=lambda x: -x[0]
    )
    topic_ids = [t["id"] for score, t in topic_scores if score >= TOPIC_THRESHOLD][:5]
    if not topic_ids:
        topic_ids = [t["id"] for score, t in topic_scores][:3]

    # ── 해시태그
    HASHTAG_THRESHOLD = 0.4
    hashtag_sims = util.cos_sim(query_vec, _get_hashtag_embeddings())[0]
    hashtag_scores = sorted(
        [(float(hashtag_sims[i].item()), HASHTAGS[i]) for i in range(len(HASHTAGS))],
        key=lambda x: -x[0]
    )
    hashtag_names = [h["name"] for score, h in hashtag_scores if score >= HASHTAG_THRESHOLD][:5]
    if not hashtag_names:
        hashtag_names = [h["name"] for score, h in hashtag_scores][:3]

    # ── 한줄 설명 생성 (GPT 호출)
    generated_explain = _make_simple_explain_with_llm(title, simple_explain, category_name)

    print(f"[AI태그추천] '{title}'")
    print(f"  → 카테고리: {category_name} (score: {float(cat_sims[cat_idx]):.3f})")
    print(f"  → 주제({len(topic_ids)}개): {[TOPICS[i-1]['name'] for i in topic_ids]}")
    print(f"  → 해시태그({len(hashtag_names)}개): {hashtag_names}")
    print(f"  → 한줄설명: {generated_explain}")

    return {
        "categoryId": category_id,
        "topicIds": topic_ids,
        "hashtagNames": hashtag_names,
        "simpleExplain": generated_explain,
    }
