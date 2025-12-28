# Daily Asset Tracker

매일 한국 시간 오전 5시에 한국투자증권(KIS) 실전 계좌의 자산 상태(잔고, 평가금액 등)를 조회하여 PostgreSQL 데이터베이스에 저장하는 FastAPI 서비스입니다.

## 기능

- **자동 스케줄링**: `APScheduler`를 사용하여 매일 05:00 KST에 자동으로 실행됩니다.
- **수동 실행**: API 엔드포인트를 통해 즉시 자산 정보를 조회하고 저장할 수 있습니다.
- **데이터 저장**:
    - `account_snapshots`: 해당 시점의 계좌 총액, 예수금, 총 평가 손익 등 저장.
    - `stock_holdings`: 해당 시점의 보유 종목별 상세 정보(수량, 평단가, 수익률 등) 저장.

## 설치 및 설정

### 1. 요구 사항

- Python 3.9+
- PostgreSQL
- 한국투자증권 API 계정 (App Key, App Secret, 계좌번호)

### 2. 설치

```bash
pip install -r requirements.txt
```

### 3. 환경 변수 설정

`.env.example` 파일을 복사하여 `.env` 파일을 생성하고, 아래 내용을 채워주세요.

```bash
cp .env.example .env
```

**.env 파일 내용:**

```ini
# Database Configuration
DB_USER=your_user          # DB 사용자명
DB_PASSWORD=your_password  # DB 비밀번호
DB_HOST=localhost          # DB 호스트 주소
DB_PORT=5432               # DB 포트
DB_NAME=your_db_name       # DB 이름

# KIS API Configuration (Real)
KIS_APP_KEY=your_app_key         # 한국투자증권 App Key
KIS_APP_SECRET=your_app_secret   # 한국투자증권 App Secret
KIS_CANO=12345678                # 종합계좌번호 앞 8자리
KIS_ACNT_PRDT_CD=01              # 계좌 상품코드 (보통 01)
KIS_BASE_URL=https://openapi.koreainvestment.com:9443 # 실전투자 URL
```

## 실행

```bash
uvicorn daily_asset_tracker.main:app --reload
```

- 서버가 실행되면 자동으로 스케줄러가 시작됩니다.
- Swagger UI: `http://localhost:8000/docs`

> **주의**: 이 서비스는 FastAPI 프로세스 내부에서 스케줄러를 실행합니다. `gunicorn` 등을 사용하여 여러 워커(worker)로 실행할 경우, 각 프로세스마다 스케줄러가 실행되어 작업이 중복될 수 있습니다. 단일 프로세스로 실행하거나 별도의 스케줄러 프로세스를 분리하는 것을 권장합니다.

## API 사용법

### 수동 업데이트 트리거

```http
POST /manual-fetch
```

백그라운드에서 즉시 KIS API를 호출하여 최신 계좌 정보를 DB에 저장합니다.

## 개발 및 테스트

테스트 실행:

```bash
python -m unittest daily_asset_tracker/tests.py
```
