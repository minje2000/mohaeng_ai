FROM python:3.11-slim

# timezone 설정에 필요한 패키지 설치
RUN apt-get update && apt-get install -y tzdata

ENV TZ=Asia/Seoul

# 시스템 시간 기준을 한국으로 변경
RUN ln -snf /usr/share/zoneinfo/$TZ /etc/localtime && \
    echo $TZ > /etc/timezone

# 작업 디렉토리 생성
WORKDIR /app

# requirements 먼저 복사
COPY requirements.txt .

# 패키지 설치
RUN pip install --no-cache-dir -r requirements.txt

# 프로젝트 전체 복사
COPY . .

# FastAPI 포트
EXPOSE 8000

# FastAPI 실행
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]