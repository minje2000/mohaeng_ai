# 모행 AI 챗봇 개요

모행 AI 챗봇은 프론트엔드 React, 메인 백엔드 Spring Boot, AI 서버 FastAPI 구조로 나뉜다.
프론트는 사용자의 질문을 /api/ai/chat 으로 보내고, Spring Boot는 Authorization 헤더를 유지한 채 FastAPI /ai/chat 으로 전달한다.
AI 서버는 두 가지 정보를 합쳐서 답한다.
1. data/rag 아래의 프로젝트 문서
2. Spring Boot API 에서 조회한 실제 행사/마이페이지 데이터

이 구조를 쓰면 사이트 안에서 실제 서비스처럼 보이는 챗봇을 만들 수 있고, 로그인 사용자는 개인 데이터까지 반영한 답변을 받을 수 있다.
