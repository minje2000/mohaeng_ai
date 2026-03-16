from pydantic import BaseModel
from typing import Optional

class BizOcrRequest(BaseModel):
    imageBase64: str                    # Base64 인코딩된 사업자등록증 이미지

class BizOcrResponse(BaseModel):
    # OCR 추출 정보
    businessNumber: str                 # 사업자등록번호 (000-00-00000)
    companyName: str                    # 법인명 / 상호
    ownerName: str                      # 대표자 성명
    openDate: str                       # 개업일 (YYYYMMDD)
    # 국세청 검증 결과
    isValid: Optional[bool] = None      # True: 유효, False: 무효, None: 검증 생략
    validationStatus: Optional[str] = None   # VALID | INVALID | API_KEY_MISSING | API_ERROR
    validationMessage: Optional[str] = None  # 검증 결과 메시지
