import os
import re
import json
import httpx
from openai import AsyncOpenAI

client = AsyncOpenAI(api_key=os.getenv("OPENAI_API_KEY"))

# 네이버 클로바 OCR
CLOVA_OCR_URL    = os.getenv("CLOVA_OCR_URL", "https://clovaocr-api-kr.ncloud.com/external/v1/50770/0cc063b7cc3f4fed1089274482ebef09e2e6f318c9c4cd90831879a529fa54e0")
CLOVA_OCR_SECRET = os.getenv("CLOVA_OCR_SECRET", "VE1nc2JYS3NGcWhmcWJUT2RvbEtMcVZNUVpLQVVHaHE=")


def extract_open_date_from_text(ocr_text: str) -> str:
    """OCR 텍스트에서 개업연월일만 정확히 추출 (생년월일 제외)"""
    lines = ocr_text.split("\n")

    # "개업" 키워드가 있는 줄 인덱스 찾기
    open_idx = -1
    for i, line in enumerate(lines):
        if "개업" in line:
            open_idx = i
            break

    if open_idx == -1:
        return ""

    # 개업 키워드 앞뒤 8줄 범위에서 탐색
    search_lines = lines[max(0, open_idx - 8): open_idx + 8]
    search_text = " ".join(search_lines)
    print(f"[개업일 탐색 범위]: {search_text}")

    # 패턴 1: 정상 - "YYYY년 MM월 DD일" or "YYYY LM MM월 DD일"
    match = re.search(r"(20\d{2})\s*[년LlMmu]\s*(\d{1,2})\s*[월]\s*(\d{1,2})", search_text)
    if match:
        y, m, d = match.group(1), match.group(2).zfill(2), match.group(3).zfill(2)
        print(f"[개업일 추출 패턴1]: {y}{m}{d}")
        return f"{y}{m}{d}"

    # 패턴 2: OCR 노이즈 - "20XX [노이즈] MM [노이즈] DD" (연도만 20xx로 시작하는 것)
    # 생년월일(1900년대) 제외하기 위해 반드시 20으로 시작하는 연도만
    match = re.search(r"(20\d{2})\D{1,10}?(\d{1,2})\s*0?(\d{2})\b", search_text)
    if match:
        y, m, d = match.group(1), match.group(2).zfill(2), match.group(3).zfill(2)
        print(f"[개업일 추출 패턴2]: {y}{m}{d}")
        return f"{y}{m}{d}"

    return ""

# 국세청 사업자등록 진위확인 API
NTS_API_KEY = os.getenv("NTS_API_KEY", "")


# ─────────────────────────────────────────
# 1. 클로바 OCR → 텍스트 추출
# ─────────────────────────────────────────
async def extract_text_with_clova(image_base64: str) -> str:
    """네이버 클로바 OCR로 이미지에서 텍스트 추출"""
    headers = {
        "X-OCR-SECRET": CLOVA_OCR_SECRET,
        "Content-Type": "application/json",
    }
    body = {
        "version": "V2",
        "requestId": "biz-ocr-001",
        "timestamp": 0,
        "lang": "ko",
        "images": [
            {
                "format": "jpg",
                "name": "biz_registration",
                "data": image_base64,
            }
        ],
        "enableTableDetect": False,
    }

    async with httpx.AsyncClient(timeout=15) as http:
        res = await http.post(CLOVA_OCR_URL, json=body, headers=headers)
        print(f"[CLOVA OCR] 응답 코드: {res.status_code}")
        print(f"[CLOVA OCR] 응답 내용: {res.text[:500]}")
        if res.status_code != 200:
            raise Exception(f"클로바 OCR 오류: {res.status_code} {res.text}")

        data = res.json()
        # 인식된 텍스트 전체 합치기
        texts = []
        for image in data.get("images", []):
            for field in image.get("fields", []):
                texts.append(field.get("inferText", ""))

        full_text = "\n".join(texts)
        print(f"[CLOVA OCR] 추출 텍스트:\n{full_text}")
        return full_text


# ─────────────────────────────────────────
# 2. GPT → 클로바 텍스트에서 필드 파싱
# ─────────────────────────────────────────
async def parse_biz_info_with_gpt(ocr_text: str) -> dict:
    """클로바가 추출한 텍스트를 GPT가 구조화된 JSON으로 파싱"""
    response = await client.chat.completions.create(
        model="gpt-4o",
        temperature=0,
        messages=[
            {
                "role": "system",
                "content": "당신은 사업자등록증 텍스트에서 정보를 추출하는 전문가입니다. 반드시 JSON만 반환하세요."
            },
            {
                "role": "user",
                "content": f"""아래는 대한민국 사업자등록증 OCR 텍스트입니다.
각 필드를 정확히 추출해주세요.

OCR 텍스트:
{ocr_text}

반드시 아래 JSON 형식만 반환하고 다른 텍스트는 포함하지 마세요:
{{
  "businessNumber": "000-00-00000",
  "companyName": "상호명",
  "ownerName": "대표자 성명",
  "birthDate": "YYYYMMDD",
  "openDate": "YYYYMMDD"
}}

각 필드 추출 방법:

[businessNumber]
- "등록번호" 옆 숫자, 반드시 하이픈 포함 000-00-00000 형식

[companyName]
- "상 호" 또는 "법인명(단체명)" 옆 텍스트

[ownerName]
- "성 명" 또는 "대 표 자" 옆 이름
- "성명 : [이름]   생년월일 : [날짜]" 구조에서 [이름] 부분만 추출
- 절대 날짜나 숫자를 넣지 말 것

[birthDate]
- "생년월일" 옆 날짜 (대표자 개인 생년월일)
- 텍스트에서 첫번째로 나오는 날짜가 생년월일임
- YYYYMMDD 형식 (예: 19650301)

[openDate]
- "개업연월일" 옆 날짜 (사업 시작일)
- 텍스트에서 두번째로 나오는 날짜가 개업일임
- 생년월일보다 반드시 나중에 나오는 날짜
- YYYYMMDD 형식 (예: 20121201)
- OCR 노이즈로 글자가 깨져 있어도 최대한 유추해서 반환"""
            }
        ],
        max_tokens=300,
    )

    raw = response.choices[0].message.content.strip()
    print(f"[GPT 파싱] 결과: {raw}")

    if raw.startswith("```"):
        raw = raw.split("```")[1]
        if raw.startswith("json"):
            raw = raw[4:]

    return json.loads(raw.strip())


# ─────────────────────────────────────────
# 3. 국세청 API → 사업자 유효성 검증
# ─────────────────────────────────────────
async def verify_biz_registration(business_number: str, owner_name: str, open_date: str) -> dict:
    if not NTS_API_KEY:
        return {"valid": None, "status": "API_KEY_MISSING", "message": "국세청 API 키가 설정되지 않았습니다."}

    biz_num_clean = business_number.replace("-", "")
    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Infuser {NTS_API_KEY}",
    }

    async with httpx.AsyncClient(timeout=10) as http:
        # Step 1: 상태 조회 (폐업/휴업 여부 확인)
        status_res = await http.post(
            "https://api.odcloud.kr/api/nts-businessman/v1/status",
            json={"b_no": [biz_num_clean]},
            headers=headers,
        )
        status_data = status_res.json()
        print(f"[국세청 상태조회] {status_data}")

        status_results = status_data.get("data", [])
        if not status_results:
            return {"valid": False, "status": "NOT_FOUND", "message": "등록되지 않은 사업자번호입니다."}

        r = status_results[0]
        b_stt_cd = r.get("b_stt_cd", "")
        b_stt    = r.get("b_stt", "")
        tax_type = r.get("tax_type", "")
        print(f"[국세청 상태] {b_stt} ({b_stt_cd})")

        if b_stt_cd == "02":
            return {"valid": False, "status": "SUSPENDED", "message": "휴업 중인 사업자입니다."}
        if b_stt_cd == "03":
            return {"valid": False, "status": "CLOSED",    "message": "폐업한 사업자입니다."}
        if "등록되지 않은" in tax_type:
            return {"valid": False, "status": "NOT_FOUND", "message": "등록되지 않은 사업자번호입니다."}

        # Step 2: 진위확인 (대표자명 + 개업일 일치 여부)
        if not open_date or not owner_name:
            return {"valid": False, "status": "MISSING_FIELD",
                    "message": "개업일자 또는 대표자명을 인식하지 못했습니다. 더 선명한 이미지로 다시 시도해주세요."}

        validate_res = await http.post(
            "https://api.odcloud.kr/api/nts-businessman/v1/validate",
            json={"businesses": [{"b_no": biz_num_clean, "start_dt": open_date, "p_nm": owner_name}]},
            headers=headers,
        )
        validate_data = validate_res.json()
        print(f"[국세청 진위확인] {validate_data}")

        validate_results = validate_data.get("data", [])
        if not validate_results:
            return {"valid": False, "status": "VALIDATE_ERROR", "message": "진위확인 조회 실패"}

        valid_cd = validate_results[0].get("valid", "02")
        if valid_cd == "01":
            return {"valid": True,  "status": "VALID",   "message": f"인증 완료 ({tax_type})"}
        else:
            return {"valid": False, "status": "INVALID", "message": "사업자 정보가 일치하지 않습니다. (대표자명 또는 개업일 불일치)"}


# ─────────────────────────────────────────
# 4. 메인: 클로바 OCR + GPT 파싱 + 국세청 검증
# ─────────────────────────────────────────
async def extract_and_verify_biz(image_base64: str) -> dict:
    # Step 1: 클로바 OCR로 텍스트 추출
    try:
        ocr_text = await extract_text_with_clova(image_base64)
    except Exception as e:
        return {
            "businessNumber": "", "companyName": "", "ownerName": "", "openDate": "",
            "isValid": False, "validationStatus": "OCR_ERROR",
            "validationMessage": f"OCR 처리 중 오류: {str(e)}",
        }

    # 이미지 품질 체크: 인식된 텍스트가 너무 적으면 화질 불량
    meaningful_lines = [l for l in ocr_text.split("\n") if len(l.strip()) > 1]
    if len(meaningful_lines) < 10:
        return {
            "businessNumber": "", "companyName": "", "ownerName": "", "openDate": "",
            "isValid": False, "validationStatus": "LOW_QUALITY",
            "validationMessage": "이미지가 너무 흐리거나 작습니다. 화질이 좋은 사업자등록증 사진으로 다시 시도해주세요.",
        }

    # Step 2: GPT로 필드 파싱
    try:
        extracted = await parse_biz_info_with_gpt(ocr_text)
    except Exception as e:
        return {
            "businessNumber": "", "companyName": "", "ownerName": "", "openDate": "",
            "isValid": False, "validationStatus": "PARSE_ERROR",
            "validationMessage": f"텍스트 파싱 중 오류: {str(e)}",
        }

    business_number = extracted.get("businessNumber", "")
    company_name    = extracted.get("companyName", "")
    owner_name      = extracted.get("ownerName", "")
    open_date       = extracted.get("openDate", "")

    # 필수 정보 누락 체크
    if not business_number or not owner_name or not open_date:
        missing = []
        if not business_number: missing.append("사업자등록번호")
        if not owner_name:      missing.append("대표자명")
        if not open_date:       missing.append("개업일자")
        return {
            "businessNumber": business_number, "companyName": company_name,
            "ownerName": owner_name, "openDate": open_date,
            "isValid": False, "validationStatus": "MISSING_FIELD",
            "validationMessage": f"{'·'.join(missing)} 인식에 실패했습니다. 더 선명하고 밝은 사업자등록증 사진으로 다시 시도해주세요.",
        }

    # Step 3: 국세청 검증
    verification = await verify_biz_registration(business_number, owner_name, open_date)

    return {
        "businessNumber":     business_number,
        "companyName":        company_name,
        "ownerName":          owner_name,
        "openDate":           open_date,
        "isValid":            verification["valid"],
        "validationStatus":   verification["status"],
        "validationMessage":  verification["message"],
    }
