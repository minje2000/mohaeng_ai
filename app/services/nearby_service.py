import os
import json
import httpx
from typing import Optional
from openai import AsyncOpenAI
from app.schemas.nearby_schema import NearbyRequest, NearbyResponse, CourseItem

client = AsyncOpenAI(api_key=os.getenv("OPENAI_API_KEY"))
GOOGLE_PLACES_KEY = os.getenv("GOOGLE_PLACES_API_KEY", "")
KAKAO_REST_KEY    = os.getenv("KAKAO_REST_API_KEY", "")

DRIVE_15MIN_RADIUS   = 12000  # 차로 15분 ≒ 12km
TRANSIT_30MIN_RADIUS =  6000  # 대중교통 30분 ≒ 6km

def get_season_info(date_str: Optional[str]) -> str:
    """행사 날짜로 계절 + 날씨 특성 반환"""
    if not date_str:
        return "계절 정보 없음"
    try:
        from datetime import datetime
        month = datetime.strptime(date_str, "%Y-%m-%d").month
    except Exception:
        return "계절 정보 없음"

    if month in (3, 4, 5):
        return (
            "계절: 봄 🌸\n"
            "- 꽃놀이, 나들이 명소, 야외 테라스 카페 적극 추천\n"
            "- 일교차 크므로 실내외 장소 균형 있게 구성\n"
            "- 벚꽃·진달래 등 봄꽃 관련 명소 우선 추천"
        )
    elif month in (6, 7, 8):
        return (
            "계절: 여름 ☀️\n"
            "- 폭염 고려해 냉방 잘 되는 실내 카페·관광지 위주 추천\n"
            "- 야외 일정은 오전 일찍 또는 저녁 이후로 배치\n"
            "- 워터파크·계곡·해변 등 물놀이 명소 우선 추천\n"
            "- 뜨거운 음식보다 냉면·빙수·냉모밀 등 계절 메뉴 있는 식당 추천"
        )
    elif month in (9, 10, 11):
        return (
            "계절: 가을 🍂\n"
            "- 단풍 명소, 억새밭, 가을 정원 등 야외 관광지 적극 추천\n"
            "- 날씨 좋은 계절이므로 야외 테라스 카페 추천\n"
            "- 전어·대하·송이버섯 등 가을 제철 음식 있는 식당 추천"
        )
    else:  # 12, 1, 2
        return (
            "계절: 겨울 ❄️\n"
            "- 추위 고려해 실내 카페·관광지 위주로 구성\n"
            "- 야외 일정은 최소화하고 이동 시간 짧게 배치\n"
            "- 뜨끈한 국밥·찜·탕 류 식당 우선 추천\n"
            "- 눈꽃 명소·크리스마스 마켓 등 겨울 특화 명소 우선 추천"
        )


# ─────────────────────────────────────────
# 1. Google Places → 별점 기반 수집
# ─────────────────────────────────────────
async def search_google_places(
    keyword: str,
    place_type: str,
    lat: float,
    lng: float,
    radius: int = DRIVE_15MIN_RADIUS,
    limit: int = 8,
) -> list[dict]:
    """별점 있는 장소만 반환, 별점 내림차순"""
    if not GOOGLE_PLACES_KEY:
        return []

    url = "https://maps.googleapis.com/maps/api/place/nearbysearch/json"
    params = {
        "location": f"{lat},{lng}",
        "radius": radius,
        "type": place_type,
        "keyword": keyword,
        "language": "ko",
        "key": GOOGLE_PLACES_KEY,
    }

    async with httpx.AsyncClient(timeout=15) as http:
        res = await http.get(url, params=params)
        if res.status_code != 200:
            return []

        places = []
        for p in res.json().get("results", []):
            rating = p.get("rating")
            if not rating:      # 별점 없으면 제외
                continue
            loc = p["geometry"]["location"]
            places.append({
                "place_name":   p.get("name", ""),
                "address":      p.get("vicinity", ""),
                "lat":          loc["lat"],
                "lng":          loc["lng"],
                "rating":       rating,
                "rating_count": p.get("user_ratings_total", 0),
                "kakao_url":    None,   # 아래 단계에서 채움
            })

        # 별점 내림차순 (동점이면 리뷰 수 많은 순)
        places.sort(key=lambda x: (x["rating"], x["rating_count"]), reverse=True)
        return places[:limit]


# ─────────────────────────────────────────
# 2. Kakao Keyword Search → place_id 매핑
#    → 상세 페이지 URL: https://place.map.kakao.com/{id}
# ─────────────────────────────────────────
async def get_kakao_place_url(place_name: str, lat: float, lng: float) -> str | None:
    """장소명 + 좌표로 카카오 place_id를 찾아 상세 페이지 URL 반환.
    카카오에 없으면 None 반환 → 해당 장소 추천에서 제외됨."""
    if not KAKAO_REST_KEY:
        return None

    url = "https://dapi.kakao.com/v2/local/search/keyword.json"
    params = {
        "query": place_name,
        "y": lat, "x": lng,
        "radius": 500,      # 반경 500m 이내에서 이름 매칭
        "size": 3,
    }
    headers = {"Authorization": f"KakaoAK {KAKAO_REST_KEY}"}

    try:
        async with httpx.AsyncClient(timeout=8) as http:
            res = await http.get(url, params=params, headers=headers)
            if res.status_code != 200:
                return None
            docs = res.json().get("documents", [])
            if not docs:
                return None
            place_id = docs[0].get("id")
            if place_id:
                return f"https://place.map.kakao.com/{place_id}"
            return None
    except Exception:
        return None


# ─────────────────────────────────────────
# 3. 카카오 확인 후 없는 장소 제거
# ─────────────────────────────────────────
async def enrich_with_kakao_urls(places: list[dict]) -> list[dict]:
    import asyncio
    urls = await asyncio.gather(*[
        get_kakao_place_url(p["place_name"], p["lat"], p["lng"])
        for p in places
    ])
    # 카카오에서 찾은 곳만 살림
    result = []
    for p, url in zip(places, urls):
        if url is None:
            continue        # 카카오에 없으면 추천 목록에서 제외
        p["kakao_url"] = url
        result.append(p)
    return result


# ─────────────────────────────────────────
# 4. 메인: 코스 생성
# ─────────────────────────────────────────
async def generate_travel_course(req: NearbyRequest) -> NearbyResponse:
    import asyncio

    # 이동 수단에 따라 반경 결정
    radius = TRANSIT_30MIN_RADIUS if req.transport == "도보" else DRIVE_15MIN_RADIUS

    # 구글에서 별점 기반 수집 (카페 1개, 맛집 최대 3개, 관광 최대 4개)
    restaurants_raw, cafes_raw, attractions_raw = await asyncio.gather(
        search_google_places("맛집 음식점", "restaurant",        req.latitude, req.longitude, radius=radius, limit=6),
        search_google_places("카페",        "cafe",              req.latitude, req.longitude, radius=radius, limit=3),
        search_google_places("관광지 명소", "tourist_attraction", req.latitude, req.longitude, radius=radius, limit=5),
    )

    # 카카오 상세 URL 일괄 주입
    restaurants, cafes, attractions = await asyncio.gather(
        enrich_with_kakao_urls(restaurants_raw),
        enrich_with_kakao_urls(cafes_raw),
        enrich_with_kakao_urls(attractions_raw),
    )

    def fmt_places(places: list[dict], label: str) -> str:
        if not places:
            return f"{label}: 정보 없음"
        lines = [
            f"  - {p['place_name']} (⭐{p['rating']} / 리뷰 {p['rating_count']}개 / {p['address']})"
            for p in places
        ]
        return f"{label}:\n" + "\n".join(lines)

    places_text = "\n".join([
        fmt_places(restaurants, "주변 맛집 (별점 높은 순)"),
        fmt_places(cafes,       "주변 카페 (별점 높은 순)"),
        fmt_places(attractions, "주변 관광지 (별점 높은 순)"),
    ])

    if req.festival_start_time and req.festival_end_time:
        festival_time_info = f"행사 운영 시간: {req.festival_start_time} ~ {req.festival_end_time}"
    elif req.festival_start_time:
        festival_time_info = f"행사 시작 시간: {req.festival_start_time}"
    else:
        festival_time_info = "행사 시간: 별도 안내 없음 (오전 10시 ~ 오후 6시로 가정)"

    # 계절 정보
    season_info = get_season_info(req.festival_date)

    system_prompt = """당신은 국내 축제 당일치기 여행 코스 전문 플래너입니다.
반드시 아래 JSON 형식만 반환하고, 다른 텍스트는 포함하지 마세요.
숙소, 조식, 숙박 관련 항목은 절대 포함하지 마세요.
카테고리는 반드시 "축제", "맛집", "카페", "관광" 중 하나만 사용하세요.

{
  "summary": "코스 한줄 소개 (50자 내외)",
  "course": [
    {
      "time": "10:00",
      "place_name": "장소명",
      "category": "축제|맛집|카페|관광",
      "description": "이 장소에서 할 것, 즐길 것 (2~3문장)",
      "tip": "꿀팁 (1문장, 없으면 null)",
      "address": "주소",
      "lat": null,
      "lng": null,
      "kakao_url": null
    }
  ]
}"""

    user_prompt = f"""
축제: {req.festival_name}
{festival_time_info}
동행: {req.companion}
이동 수단: {req.transport}

{season_info}

{places_text}

위 조건에 맞는 당일치기 코스를 짜주세요.
- {req.companion} 코스에 맞는 분위기와 동선으로 구성
- {'대중교통으로 다음 장소까지 30분 이내 이동 가능한 동선으로 구성할 것' if req.transport == '도보' else '차로 15분 이내 반경으로'}
- 행사 시간을 반드시 스케쥴 중간에 배치하고, 전후로 맛집·카페·관광지를 배치
- 위의 계절 정보를 반드시 반영해서 계절에 맞는 장소·음식·활동으로 구성할 것
- 숙소, 조식, 숙박 관련 항목은 절대 포함하지 말 것
- 카테고리는 "축제", "맛집", "카페", "관광" 중 하나만 사용
- 별점 높은 장소 위주로 선별, 별점 낮은 곳은 제외
- 카페는 반드시 1곳만 포함할 것
- 맛집(음식점)은 최대 3곳까지만 포함할 것
- 목록에 없는 장소는 추가하지 말 것 (hallucination 금지)
- course 배열에 5~7개 항목
"""

    gpt_res = await client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user",   "content": user_prompt},
        ],
        temperature=0.7,
        max_tokens=2000,
    )

    raw = gpt_res.choices[0].message.content.strip()
    if raw.startswith("```"):
        raw = raw.split("```")[1]
        if raw.startswith("json"):
            raw = raw[4:]
    parsed = json.loads(raw.strip())

    # 장소 매핑 — 카카오 상세 URL + 좌표 주입
    all_places = {p["place_name"]: p for p in restaurants + cafes + attractions}
    course_items = []
    cafe_count = 0
    restaurant_count = 0

    for item in parsed.get("course", []):
        if item.get("category") in ("숙소", "조식"):
            continue
        # 카페 1개, 맛집 3개 초과 방지 (GPT가 무시할 경우 서버에서도 컷)
        if item.get("category") == "카페":
            if cafe_count >= 1:
                continue
            cafe_count += 1
        if item.get("category") == "맛집":
            if restaurant_count >= 3:
                continue
            restaurant_count += 1

        matched = all_places.get(item.get("place_name"))
        if matched:
            item["lat"]       = matched["lat"]
            item["lng"]       = matched["lng"]
            item["address"]   = item.get("address") or matched["address"]
            item["kakao_url"] = matched["kakao_url"]   # 카카오 상세 페이지 URL
        elif item.get("lat") and item.get("lng"):
            item["kakao_url"] = f"https://map.kakao.com/link/map/{item['place_name']},{item['lat']},{item['lng']}"

        course_items.append(CourseItem(**item))

    return NearbyResponse(
        summary=parsed.get("summary", ""),
        companion=req.companion,
        course=course_items,
    )
