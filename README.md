# 모행 AI Server

본 프로젝트는 4인 팀 프로젝트로 진행되었으며,  
해당 저장소는 개인 포트폴리오 제출을 위해 정리한 사본입니다.

---

## 프로젝트 소개
본 저장소는 행사 내용의 유해성 및 위험도를 분석하는  
AI 기반 검수 기능을 담당하는 서버입니다.

---

## 프로젝트 구성
- Frontend: https://github.com/minje2000/mohaeng_front
- Backend: https://github.com/minje2000/mohaeng_back
- AI Server: https://github.com/minje2000/mohaeng_ai

---

## 기술 스택
- Python
- FastAPI
- IBM watsonx

---

## AI 검수 기능

### 입력
- 행사 제목
- 상세 설명

### 출력
- 위험 점수 (risk_score)
- 검수 결과

---

## 백엔드 연동
- Spring Boot 서버에서 API 호출
- 내부 API KEY 기반 인증 처리

---

## 목적
- 부적절하거나 위험한 행사 콘텐츠 사전 필터링
- 관리자 검수 프로세스 자동화 지원
