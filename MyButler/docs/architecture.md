# MyButler 아키텍처 문서

## 시스템 개요

MyButler는 주식 포트폴리오 기록 및 스크리닝 시스템입니다.

```
┌─────────────────────────────────────────────────────────────────┐
│                        FastAPI Application                       │
├─────────────────────────────────────────────────────────────────┤
│  Controllers (API Layer)                                         │
│  ┌──────────────┐ ┌──────────────┐ ┌──────────────┐             │
│  │   History    │ │  Screening   │ │     Tag      │             │
│  │  Controller  │ │  Controller  │ │  Controller  │             │
│  └──────┬───────┘ └──────┬───────┘ └──────┬───────┘             │
├─────────┼────────────────┼────────────────┼─────────────────────┤
│  Services (Business Logic Layer)                                 │
│  ┌──────┴───────┐ ┌──────┴───────┐ ┌──────┴───────┐             │
│  │  Recording   │ │  Screening   │ │     Tag      │             │
│  │   Service    │ │   Service    │ │   Service    │             │
│  └──────┬───────┘ └──────┬───────┘ └──────────────┘             │
│         │                │                                       │
│  ┌──────┴───────┐ ┌──────┴─────────────────────────┐            │
│  │   Balance    │ │         Analysis Services       │            │
│  │   Service    │ │  ┌───────────┐ ┌─────────────┐ │            │
│  └──────┬───────┘ │  │ Technical │ │ Fundamental │ │            │
│         │         │  │  Service  │ │   Service   │ │            │
│         │         │  └───────────┘ └─────────────┘ │            │
│         │         │  ┌───────────┐                 │            │
│         │         │  │ Ichimoku  │                 │            │
│         │         │  │  Service  │                 │            │
│         │         │  └───────────┘                 │            │
│         │         └────────────────────────────────┘            │
├─────────┼───────────────────────────────────────────────────────┤
│  External APIs & Data Layer                                      │
│  ┌──────┴───────┐ ┌──────────────┐ ┌──────────────┐             │
│  │   KIS API    │ │    SQLite    │ │    Redis     │             │
│  │   Service    │ │  (영구저장)   │ │   (캐시)     │             │
│  └──────────────┘ └──────────────┘ └──────────────┘             │
└─────────────────────────────────────────────────────────────────┘
         │
         ▼
┌─────────────────────────────────────────────────────────────────┐
│                     Scheduler (APScheduler)                      │
│  ┌──────────────────┐  ┌──────────────────┐                     │
│  │  Recording Job   │  │  Screening Job   │                     │
│  │  (평일 장마감후)   │  │   (평일 08:00)   │                     │
│  └──────────────────┘  └──────────────────┘                     │
└─────────────────────────────────────────────────────────────────┘
```

## 계층 구조

### 1. Controller Layer (API 엔드포인트)

| 컨트롤러 | 경로 | 역할 |
|---------|------|------|
| `history_controller.py` | `/api/v1/history/*` | 자산 기록 조회, 수동 기록 트리거 |
| `screening_controller.py` | `/api/v1/screening/*` | 주식 스크리닝 실행, 결과 조회 |
| `tag_controller.py` | `/api/v1/tags/*` | 자산 태그 CRUD, 종목-태그 연결 |

### 2. Service Layer (비즈니스 로직)

#### 핵심 서비스

| 서비스 | 파일 | 역할 |
|--------|------|------|
| `RecordingService` | `recording_service.py` | 일일 자산 기록 (KIS API 연동) |
| `HistoryService` | `history_service.py` | 기록 데이터 CRUD |
| `ScreeningService` | `screening_service.py` | 주식 스크리닝 통합 |
| `TagService` | `tag_service.py` | 자산 태그 관리 |

#### 분석 서비스

| 서비스 | 파일 | 역할 |
|--------|------|------|
| `IchimokuService` | `ichimoku_service.py` | 일목균형표 분석 |
| `TechnicalService` | `technical_analysis/technical_service.py` | 기술적 분석 통합 |
| `FundamentalService` | `fundamental_analysis/fundamental_service.py` | 펀더멘탈 분석 통합 |

#### 데이터 서비스

| 서비스 | 파일 | 역할 |
|--------|------|------|
| `KISStockDataService` | `kis_stock_data_service.py` | KIS API 통신 |
| `StockDataService` | `stock_data_service.py` | 주식 데이터 수집 |
| `RedisService` | `redis_service.py` | Redis 캐시 관리 |

### 3. Scheduler Layer

```
SchedulerManager (APScheduler)
    │
    ├── Recording Job
    │   └── 평일 장마감 후 실행 (미국시간 기준 자동 조정)
    │   └── DST(서머타임) 자동 대응
    │
    └── Screening Job
        └── 평일 08:00 KST 실행
```

## 데이터 흐름

### 1. 일일 자산 기록 흐름

```
[Scheduler] ─▶ [RecordingJob]
                    │
                    ▼
            [RecordingService]
                    │
        ┌───────────┴───────────┐
        ▼                       ▼
[KIS API 잔고 조회]      [BalanceService]
        │                       │
        └───────────┬───────────┘
                    ▼
            [데이터 변환]
                    │
        ┌───────────┴───────────┐
        ▼                       ▼
    [SQLite]                [Redis]
   (영구 저장)              (캐시)
```

### 2. 스크리닝 흐름

```
[API 요청] ─▶ [ScreeningController]
                    │
                    ▼
            [ScreeningService]
                    │
    ┌───────────────┼───────────────┐
    ▼               ▼               ▼
[Ichimoku]    [Technical]    [Fundamental]
 Service        Service         Service
    │               │               │
    │    ┌──────────┴──────────┐    │
    │    ▼          ▼          ▼    │
    │ Bollinger  MA정배열  컵앤핸들  │
    │    │          │          │    │
    └────┴──────────┴──────────┴────┘
                    │
                    ▼
            [점수 계산 & 필터링]
                    │
                    ▼
            [ScreeningResponse]
```

### 3. 태그 기반 자산 분류 흐름

```
[API 요청] ─▶ [TagController]
                    │
                    ▼
              [TagService]
                    │
        ┌───────────┴───────────┐
        ▼                       ▼
   [asset_tags]           [stock_tags]
    (태그 정의)           (종목-태그 매핑)
```

## 분석 모듈 상세

### 기술적 분석 (Technical Analysis)

```
TechnicalService
    │
    ├── BollingerAnalyzer
    │   └── 볼린저 밴드 스퀴즈 감지
    │   └── 점수: 최대 60점
    │
    ├── MAAlignmentAnalyzer
    │   └── 이동평균선 정배열 (5/20/60/120일)
    │   └── 점수: 최대 60점
    │
    └── CupHandleAnalyzer
        └── 컵앤핸들 패턴 감지
        └── 점수: 최대 60점
```

### 펀더멘탈 분석 (Fundamental Analysis)

```
FundamentalService
    │
    ├── ROEAnalyzer
    │   └── 자기자본이익률 분석
    │   └── 점수: 최대 30점
    │
    ├── GPMAnalyzer
    │   └── 매출총이익률 분석
    │   └── 점수: 최대 25점
    │
    ├── DebtAnalyzer
    │   └── 부채비율 분석
    │   └── 점수: 최대 25점
    │
    └── CapExAnalyzer
        └── 자본적지출 분석
        └── 점수: 최대 20점
```

### 일목균형표 (Ichimoku)

```
IchimokuService
    │
    ├── 전환선 (Tenkan-sen): 9일
    ├── 기준선 (Kijun-sen): 26일
    ├── 선행스팬A (Senkou Span A)
    ├── 선행스팬B (Senkou Span B): 52일
    ├── 후행스팬 (Chikou Span)
    └── 이격도 (Disparity): 기준선 대비

신호 조건:
    - 가격 > 구름대
    - 전환선 > 기준선
    - 후행스팬 > 26일 전 가격
    - 구름대 상승 (Span A > Span B)
    - 이격도: 적정(5~15%), 과열(>20%), 과매도(<-10%)
```

## 데이터베이스 스키마

### SQLite 테이블

```sql
-- 일일 종목 기록
daily_stock_records (
    id, record_date, exchange, currency,
    ticker, stock_name, quantity,
    avg_purchase_price, current_price,
    purchase_amount, eval_amount,
    profit_loss_amount, profit_loss_rate
)

-- 일일 요약 기록
daily_summary_records (
    id, record_date, exchange, currency,
    total_purchase_amount, total_eval_amount,
    total_profit_loss, total_profit_rate, stock_count
)

-- 기록 작업 로그
recording_logs (
    id, record_date, started_at, completed_at,
    status, exchanges_processed, total_stocks, error_message
)

-- 스크리닝 결과
screening_results (
    id, screening_date, ticker, name, market,
    current_price, signal_strength, score,
    price_above_cloud, tenkan_above_kijun, ...
)

-- 자산 태그
asset_tags (
    id, name, category, color, description
)

-- 종목-태그 매핑
stock_tags (
    id, ticker, tag_id
)
```

## 외부 의존성

### KIS API (한국투자증권)

```
사용 API:
├── 해외 잔고 조회
├── 해외 시세 조회
└── Rate Limit: kis_rate_limiter.py로 관리
```

### 주가 데이터

```
데이터 소스:
├── yfinance (미국 주식)
└── FinanceDataReader (한국 주식)
```

## 설정 파일

| 파일 | 역할 |
|------|------|
| `config.yaml` | KIS API 인증 정보 |
| `database_config.py` | DB 연결 설정 |
| `scheduler_config.py` | 스케줄러 설정 (타임존, 실행시간) |

## 확장 포인트

### 새로운 분석기 추가

```python
# 1. base_analyzer.py 상속
class NewAnalyzer(BaseAnalyzer):
    def analyze(self, df, ticker, name, market):
        ...

# 2. TechnicalService에 등록
self.analyzers["new"] = NewAnalyzer()
```

### 새로운 거래소 추가

```python
# scheduler_config.py의 target_exchanges에 추가
target_exchanges = [
    ("NASD", "USD", "NASDAQ"),
    ("NYSE", "USD", "NYSE"),
    ("NEW_EX", "XXX", "New Exchange"),  # 추가
]
```

## 성능 고려사항

1. **비동기 처리**: aiosqlite, redis.asyncio 사용
2. **병렬 스크리닝**: ThreadPoolExecutor로 다중 종목 동시 분석
3. **캐싱**: Redis에 최근 데이터 캐시 (TTL 7일)
4. **Rate Limiting**: KIS API 호출 제한 관리
