import os
import json
import re
import httpx

# CLOVA OCR 설정
CLOVA_OCR_URL = os.getenv("CLOVA_OCR_URL")
CLOVA_OCR_SECRET = os.getenv("CLOVA_OCR_SECRET")


# 1. CLOVA BizLicense OCR 호출
async def extract_biz_license_with_clova(image_base64: str) -> dict:

    headers = {
        "X-OCR-SECRET": CLOVA_OCR_SECRET,
        "Content-Type": "application/json",
    }

    body = {
        "version": "V2",
        "requestId": "biz-license-ocr",
        "timestamp": 0,
        "images": [
            {
                "format": "jpg",
                "name": "biz-license",
                "data": image_base64,
            }
        ]
    }

    async with httpx.AsyncClient(timeout=20) as http:

        res = await http.post(CLOVA_OCR_URL, headers=headers, json=body)

        print(f"[CLOVA OCR] status: {res.status_code}")
        # print(f"[CLOVA OCR] body: {res.text[:500]}")

        if res.status_code != 200:
            raise Exception(f"CLOVA OCR 오류: {res.status_code} {res.text}")

        return res.json()


# OCR 문자 오류 보정
def normalize_text(text: str):

    replace_map = {
        "O": "0",
        "o": "0",
        "I": "1",
        "l": "1",
        "S": "5",
        "B": "8",
        "Z": "2",
        "G": "6",
    }

    for k, v in replace_map.items():
        text = text.replace(k, v)

    return text


# 날짜 수정
def normalize_date(text: str):

    text = normalize_text(text)

    nums = re.findall(r"\d+", text)

    if len(nums) < 3:
        return ""

    year = nums[0]
    month = nums[1][-2:]
    day = nums[2][-2:]

    try:

        month = int(month)
        day = int(day)

        if month > 12:
            month = int(str(month)[-1])

        if day > 31:
            day = int(str(day)[-1])

        return f"{year}{str(month).zfill(2)}{str(day).zfill(2)}"

    except:
        return ""


# 사업자번호 추출 (보정)
def extract_business_number(text):

    text = normalize_text(text)

    m = re.search(r"\d{3}-\d{2}-\d{5}", text)

    if m:
        return m.group()

    # 하이픈 없는 경우
    nums = re.findall(r"\d+", text)

    if len(nums) >= 3:
        a = nums[0][-3:]
        b = nums[1][-2:]
        c = nums[2][-5:]

        return f"{a}-{b}-{c}"

    return ""


# 회사명 정리
def normalize_company_name(name):

    name = name.strip()

    noise = [
        "주식회사",
        "(주)",
        "㈜",
    ]

    for n in noise:
        name = name.replace(n, "").strip()

    return name


# BizLicense 결과 파싱
def parse_biz_license(data: dict) -> dict:

    images = data.get("images", [])

    if not images:
        return {}

    biz = images[0].get("bizLicense", {})
    result = biz.get("result", {})

    register_number = ""
    rep_name = ""
    open_date = ""
    company_name = ""
    tax_type = ""

    text_dump = json.dumps(result, ensure_ascii=False)

    # 사업자번호
    if result.get("registerNumber"):
        raw = result["registerNumber"][0].get("text", "")
        register_number = extract_business_number(raw)

    if not register_number:
        register_number = extract_business_number(text_dump)

    # 대표자
    if result.get("repName"):
        rep_name = result["repName"][0].get("text", "")

    if not rep_name:

        m = re.search(r"(대표자|성명)\s*[:：]?\s*([가-힣]{2,4})", text_dump)

        if m:
            rep_name = m.group(2)

    # 회사명
    if result.get("companyName"):
        company_name = result["companyName"][0].get("text", "")

    if not company_name and result.get("corpName"):
        company_name = result["corpName"][0].get("text", "")

    if not company_name and result.get("bisName"):
        company_name = result["bisName"][0].get("text", "")

    company_name = normalize_company_name(company_name)

    # fallback
    if not company_name:

        m = re.search(r"(상호|법인명).*?([가-힣A-Za-z0-9]{2,})", text_dump)

        if m:
            company_name = m.group(2)

    # 개업연월일
    if result.get("openDate"):

        raw = result["openDate"][0].get("text", "")
        open_date = normalize_date(raw)

    if not open_date:

        m = re.search(r"\d{4}.\d{1,2}.\d{1,2}", text_dump)

        if m:
            open_date = normalize_date(m.group())

    # 과세 유형
    if result.get("taxType"):
        tax_type = result["taxType"][0].get("text", "")

    # 디버그 출력
    # print(f"biz : {biz}")
    # print(f"register_number : {register_number}")
    # print(f"rep_name : {rep_name}")
    # print(f"open_date : {open_date}")
    # print(f"company_name : {company_name}")
    # print(f"tax_type : {tax_type}")

    return {
        "businessNumber": register_number,
        "companyName": company_name,
        "ownerName": rep_name,
        "openDate": open_date,
        "taxType": tax_type,
    }


# -------------------------------------------------
# 전체 실행 함수
# -------------------------------------------------
async def extract_and_verify_biz(image_base64: str) -> dict:

    try:

        ocr_result = await extract_biz_license_with_clova(image_base64)

    except Exception as e:

        return {
            "businessNumber": "",
            "companyName": "",
            "ownerName": "",
            "openDate": "",
            "taxType": "",
            "validationStatus": "OCR_ERROR",
            "validationMessage": str(e),
        }

    try:

        parsed = parse_biz_license(ocr_result)

    except Exception as e:

        return {
            "businessNumber": "",
            "companyName": "",
            "ownerName": "",
            "openDate": "",
            "taxType": "",
            "validationStatus": "PARSE_ERROR",
            "validationMessage": str(e),
        }

    return {
        "businessNumber": parsed.get("businessNumber", ""),
        "companyName": parsed.get("companyName", ""),
        "ownerName": parsed.get("ownerName", ""),
        "openDate": parsed.get("openDate", ""),
        "taxType": parsed.get("taxType", ""),
        "validationStatus": None,
        "validationMessage": None,
    }