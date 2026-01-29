# MyButler Services Documentation

## 서비스 개요

| 서비스 | 파일 | 역할 |
|--------|------|------|
| ScreeningService | screening_service.py | 주식 스크리닝 (일목균형표 + 기술적 분석) |
| IchimokuService | ichimoku_service.py | 일목균형표 계산 및 신호 분석 |
| **TechnicalService** | technical_analysis/technical_service.py | 통합 기술적 분석 서비스 |
| **BollingerAnalyzer** | technical_analysis/bollinger_analyzer.py | 볼린저 밴드 스퀴즈 분석 |
| **MAAlignmentAnalyzer** | technical_analysis/ma_alignment_analyzer.py | 이동평균선 정배열 분석 |
| **CupHandleAnalyzer** | technical_analysis/cup_handle_analyzer.py | 컵 앤 핸들 패턴 분석 |
| StockDataService | stock_data_service.py | 주식 데이터 수집 (yfinance, pykrx) |
| RecordingService | recording_service.py | 일일 주식 기록 비즈니스 로직 |
| HistoryService | history_service.py | SQLite 히스토리 조회 |
| RedisService | redis_service.py | Redis 캐시 관리 |

---

## 1. ScreeningService

**파일**: `app/services/screening_service.py`

### 역할
일목균형표 + 기술적 분석 필터 기반으로 미국/한국 주식을 스크리닝하여 매수 신호를 찾음

### 사용 가능한 필터

| 필터 | 설명 | 최대 점수 |
|------|------|----------|
| `ichimoku` | 일목균형표 분석 | 100점 |
| `bollinger` | 볼린저 밴드 스퀴즈 (에너지 응축형) | 80점 |
| `ma_alignment` | 이동평균선 정배열 (추세 확정형) | 95점 |
| `cup_handle` | 컵 앤 핸들 패턴 (매집 확인형) | 100점 |

### 필터 조합 모드

| 모드 | 설명 |
|------|------|
| `any` (OR) | 선택한 필터 중 하나라도 충족 |
| `all` (AND) | 선택한 필터 모두 충족 |

### 흐름도
```
run_screening(market, min_score, perfect_only, limit, filters, combine_mode)
    │
    ├─→ 미국 주식 스크리닝 (market=US or ALL)
    │       ├─ get_filtered_us_stocks() → 거래대금 필터
    │       ├─ _analyze_stocks()
    │       │   ├─ ichimoku_service.analyze_signal() (ichimoku 필터)
    │       │   ├─ technical_service.analyze_stock() (기술적 분석 필터)
    │       │   ├─ _passes_all_filters() or _passes_any_filter()
    │       │   └─ _calculate_cross_filter_bonus()
    │       └─ 점수순 정렬
    │
    ├─→ 한국 주식 스크리닝 (market=KR or ALL)
    │       └─ (동일 로직)
    │
    ├─→ 신호 강도별 분류
    │
    └─→ ScreeningResponse 반환
```

### 주요 메서드

| 메서드 | 파라미터 | 반환 | 설명 |
|--------|----------|------|------|
| `run_screening()` | market, min_score, perfect_only, limit, filters, combine_mode | ScreeningResponse | 전체 스크리닝 실행 |
| `run_bollinger_screening()` | market, min_score, limit | ScreeningResponse | 볼린저 스퀴즈 전용 |
| `run_ma_alignment_screening()` | market, min_score, limit | ScreeningResponse | 이평선 정배열 전용 |
| `run_cup_handle_screening()` | market, min_score, limit | ScreeningResponse | 컵앤핸들 전용 |
| `screen_us_stocks()` | min_score, perfect_only, max_workers, filters, combine_mode | (signals, scanned, passed) | 미국 주식 스크리닝 |
| `screen_kr_stocks()` | min_score, perfect_only, market, max_workers, filters, combine_mode | (signals, scanned, passed) | 한국 주식 스크리닝 |
| `save_screening_results()` | signals, screening_date | saved_count | DB 저장 (async) |
| `get_screening_history()` | 필터 조건들 | (records, total_count) | 히스토리 조회 (async) |
| `get_latest_recommendations()` | market, limit | Dict | 최신 추천 종목 (async) |

### 보너스 점수 시스템

다중 필터 충족 시 보너스 점수 부여:
- 2개 필터 충족: +10점
- 3개 필터 충족: +20점

### 의존성
- StockDataService
- IchimokuService
- **TechnicalService**
- database_config (SQLite)

---

## 2. IchimokuService

**파일**: `app/services/ichimoku_service.py`

### 역할
일목균형표 지표 계산 및 매수/매도 신호 분석

### 일목균형표 지표

| 지표 | 계산 방법 | 기간 |
|------|-----------|------|
| 전환선 (Tenkan) | (9일 최고 + 9일 최저) / 2 | 9일 |
| 기준선 (Kijun) | (26일 최고 + 26일 최저) / 2 | 26일 |
| 선행스팬A | (전환선 + 기준선) / 2, 26일 선행 | 26일 shift |
| 선행스팬B | (52일 최고 + 52일 최저) / 2, 26일 선행 | 52일, 26일 shift |
| 후행스팬 | 현재 종가, 26일 후행 | -26일 shift |

### 점수 계산

| 조건 | 충족 시 | 미충족 시 |
|------|---------|-----------|
| 주가 > 구름 상단 | +30 | 구름 안: +10, 구름 아래: -20 |
| 전환선 > 기준선 | +20 | -10 |
| 후행스팬 > 26일전 주가 | +20 | -10 |
| 양운 (선행A > 선행B) | +10 | -5 |
| 구름대 돌파 (5일 내) | +15 | 0 |
| 골든크로스 (5일 내) | +10 | 0 |

**점수 범위**: -100 ~ 100

### 신호 강도

| 점수 | 강도 |
|------|------|
| 80 ~ 100 | STRONG_BUY |
| 50 ~ 79 | BUY |
| 20 ~ 49 | WEAK_BUY |
| -20 ~ 19 | NEUTRAL |
| -50 ~ -21 | WEAK_SELL |
| -80 ~ -51 | SELL |
| -100 ~ -81 | STRONG_SELL |

### 주요 메서드

| 메서드 | 설명 |
|--------|------|
| `calculate_ichimoku(df)` | 일목균형표 지표 계산 |
| `analyze_signal(df, ticker, name, market)` | 종목 신호 분석 → IchimokuSignal |
| `get_buy_signals(signals, min_score)` | 매수 신호 필터링 |
| `get_perfect_signals(signals)` | 완벽 조건 신호만 필터링 |

### 완벽 조건
- 주가 > 구름대
- 전환선 > 기준선
- 후행스팬 > 26일전 주가

---

## 3. TechnicalService (NEW)

**파일**: `app/services/technical_analysis/technical_service.py`

### 역할
볼린저, 이평선 정배열, 컵앤핸들 분석기를 통합 관리

### 구조
```
app/services/technical_analysis/
├── __init__.py
├── base_analyzer.py         # 기본 분석기 인터페이스
├── bollinger_analyzer.py    # 볼린저 스퀴즈
├── ma_alignment_analyzer.py # 이평선 정배열
├── cup_handle_analyzer.py   # 컵앤핸들 패턴
└── technical_service.py     # 통합 서비스
```

### 점수 임계값
각 필터가 "충족"으로 판단되는 기준: **40점 이상**

### 주요 메서드

| 메서드 | 설명 |
|--------|------|
| `analyze_stock(df, ticker, name, market, filters)` | 단일 종목 분석 → TechnicalSignal |
| `analyze_stocks_batch(stocks_data, filters, max_workers)` | 배치 분석 |
| `get_bollinger_squeeze_signals(signals, min_score)` | 볼린저 신호 필터링 |
| `get_ma_alignment_signals(signals, min_score)` | 이평선 신호 필터링 |
| `get_cup_handle_signals(signals, min_score)` | 컵앤핸들 신호 필터링 |
| `filter_by_combine_mode(signals, filters, combine_mode, min_score)` | 조합 모드 필터링 |

### 의존성
- BollingerAnalyzer
- MAAlignmentAnalyzer
- CupHandleAnalyzer

---

## 4. BollingerAnalyzer (NEW)

**파일**: `app/services/technical_analysis/bollinger_analyzer.py`

### 역할
볼린저 밴드 스퀴즈 & 거래량 급증 분석 (에너지 응축형)

### 지표 계산

| 지표 | 공식 |
|------|------|
| 중심선 (Middle) | 20일 SMA |
| 상단 밴드 (Upper) | Middle + 2σ |
| 하단 밴드 (Lower) | Middle - 2σ |
| 밴드폭 (BandWidth) | (Upper - Lower) / Middle × 100 |
| %B | (Close - Lower) / (Upper - Lower) |

### 점수 계산 (최대 80점)

| 조건 | 점수 |
|------|------|
| 스퀴즈 (BandWidth 하위 20%) | +25 |
| 강한 스퀴즈 (하위 10%) | +35 (중복 불가) |
| 거래량 2배 이상 급증 | +20 |
| 거래량 3배 이상 | +30 (중복 불가) |
| 밴드 상단 돌파 시도 (%B ≥ 0.8) | +15 |

### 최소 데이터 요구량
60일 (백분위 계산용)

### 주요 메서드

| 메서드 | 설명 |
|--------|------|
| `calculate_bollinger_bands(df)` | 볼린저 밴드 계산 |
| `analyze(df, ticker, name, market)` | 분석 → BollingerSignal |

---

## 5. MAAlignmentAnalyzer (NEW)

**파일**: `app/services/technical_analysis/ma_alignment_analyzer.py`

### 역할
이동평균선 정배열 & 골든크로스 분석 (추세 확정형)

### 지표 계산

| 지표 | 설명 |
|------|------|
| SMA_5 | 5일 단순이동평균 |
| SMA_20 | 20일 단순이동평균 |
| SMA_60 | 60일 단순이동평균 |
| SMA_120 | 120일 단순이동평균 |
| 이격도 | (Price - SMA_20) / SMA_20 × 100 |

### 정배열 조건
```
완전 정배열: Price > SMA_5 > SMA_20 > SMA_60 > SMA_120
부분 정배열: 4단계 중 3단계 충족
```

### 점수 계산 (최대 95점)

| 조건 | 점수 |
|------|------|
| 완전 정배열 | +40 |
| 부분 정배열 (3단계) | +25 (중복 불가) |
| 단기 골든크로스 (5/20) | +10 |
| 중기 골든크로스 (20/60) | +15 |
| 장기 골든크로스 (60/120) | +20 |
| 이격도 적정 (5~15%) | +10 |
| 이격도 과열 (>15%) | -20 |

### 최소 데이터 요구량
130일 (120일 이평 + 여유분)

### 주요 메서드

| 메서드 | 설명 |
|--------|------|
| `calculate_moving_averages(df)` | 이동평균 계산 |
| `analyze(df, ticker, name, market)` | 분석 → MAAlignmentSignal |

---

## 6. CupHandleAnalyzer (NEW)

**파일**: `app/services/technical_analysis/cup_handle_analyzer.py`

### 역할
컵 앤 핸들 차트 패턴 탐지 (매집 확인형)

### 패턴 조건

| 구분 | 조건 |
|------|------|
| 컵 기간 | 60~130일 (3~6개월) |
| 컵 깊이 | 좌측 고점 대비 15~40% 하락 |
| 우측 고점 | 좌측 고점의 90~110% |
| 핸들 깊이 | 우측 고점 대비 5~15% 눌림 |

### 패턴 시각화
```
        좌측 고점          우측 고점
           │                 │
           │   ╲         ╱   │
           │    ╲       ╱    │   ╱ (핸들)
           │     ╲     ╱     │  ╱
           │      ╲   ╱      │ ╱
           │       ╲_╱       │╱
           │      바닥        │
           │                 │
       ────┴─────────────────┴────→ 시간
              컵 (60~130일)
```

### 점수 계산 (최대 100점)

| 조건 | 점수 |
|------|------|
| 컵 패턴 감지 | +25 |
| 핸들 패턴 감지 | +15 |
| 돌파 임박 (전고점 -3% 이내) | +15 |
| 돌파 확정 (전고점 상회) | +25 (중복 불가) |
| 거래량 2배 이상 | +20 |

### 최소 데이터 요구량
150일 (130일 + 여유분)

### 주요 메서드

| 메서드 | 설명 |
|--------|------|
| `analyze(df, ticker, name, market)` | 분석 → CupHandleSignal |
| `_find_cup_pattern(df)` | 컵 패턴 탐색 |
| `_find_handle_pattern(df, cup_end_idx, right_peak)` | 핸들 패턴 탐색 |

---

## 7. StockDataService

**파일**: `app/services/stock_data_service.py`

### 역할
미국/한국 주식 데이터 수집 (OHLCV)

### 데이터 소스

| 시장 | 라이브러리 | 대상 |
|------|------------|------|
| 미국 | yfinance | S&P 500 + NASDAQ 100 (중복 제거, ~550종목) |
| 한국 | pykrx | 코스피200 + 코스피150 + KRX300 (중복 제거, ~400종목) |

### 데이터 수집 기간
**200일** (컵앤핸들 패턴 분석 지원을 위해 100일 → 200일 확장)

### 미국 주식 목록 조회
- **소스**: Wikipedia
  - S&P 500: https://en.wikipedia.org/wiki/List_of_S%26P_500_companies
  - NASDAQ 100: https://en.wikipedia.org/wiki/Nasdaq-100
- **처리**: 두 지수 합산 후 중복 제거
- **캐싱**: 하루 1회 (당일 캐시 유효)
- **Fallback**: 조회 실패 시 주요 60개 종목 사용

### 한국 지수 코드

| 지수 | 코드 | 설명 |
|------|------|------|
| KOSPI200 | 1028 | 코스피 시가총액 상위 200 |
| KOSPI150 | 1034 | 코스피 대형주 150 |
| KRX300 | 1005 | 코스피 + 코스닥 대표 300 |

### 거래대금 필터

| 시장 | 최소 거래대금 (5일 평균) |
|------|-------------------------|
| 미국 | $20,000,000 |
| 한국 | 50억원 |

### 주요 메서드

| 메서드 | 설명 |
|--------|------|
| `get_us_stock_list()` | 미국 주요 종목 목록 |
| `get_kr_stock_list(market)` | 한국 종목 목록 (KOSPI/KOSDAQ/ALL) |
| `get_us_ohlcv(ticker, period_days=200)` | 미국 주식 OHLCV |
| `get_kr_ohlcv(ticker, period_days=200)` | 한국 주식 OHLCV |
| `filter_by_trading_value(df, min_value, avg_days)` | 거래대금 필터 |
| `get_filtered_us_stocks(min_trading_value, max_workers)` | 필터링된 미국 주식 + 데이터 |
| `get_filtered_kr_stocks(min_trading_value, market, max_workers)` | 필터링된 한국 주식 + 데이터 |

### 반환 데이터 컬럼
`Open, High, Low, Close, Volume, Value`

---

## 8. RecordingService

**파일**: `app/services/recording_service.py`

### 역할
일일 주식 잔고 기록 (한국투자증권 API → Redis + SQLite)

### 흐름도
```
record_all_exchanges(record_date, target_exchanges)
    │
    ├─ 거래일 확인 (should_record_today)
    │   └─ 휴장일이면 스킵
    │
    ├─ 기록 로그 생성 (history_service)
    │
    ├─ Redis 상태 업데이트 (is_running: true)
    │
    ├─ 각 거래소별 기록 (record_exchange)
    │   ├─ 잔고 조회 (balance_service.get_overseas_balance)
    │   ├─ 데이터 변환 (StockRecordCreate, SummaryRecordCreate)
    │   ├─ Redis 캐시 저장
    │   └─ SQLite 영구 저장
    │
    ├─ 상태 결정 (SUCCESS / PARTIAL / FAILED)
    │
    └─ 기록 로그 업데이트 + Redis 상태 초기화
```

### 주요 메서드

| 메서드 | 설명 |
|--------|------|
| `record_exchange(exchange, currency, record_date)` | 단일 거래소 기록 |
| `record_all_exchanges(record_date, target_exchanges)` | 전체 거래소 기록 |
| `get_recording_status()` | 기록 작업 상태 조회 |

### 의존성
- BalanceService (한국투자증권 API)
- HistoryService
- RedisService
- SchedulerConfig

---

## 9. HistoryService

**파일**: `app/services/history_service.py`

### 역할
SQLite 기반 주식 기록 영구 저장 및 조회

### 테이블 구조

**daily_stock_records** (종목별 기록)
- record_date, exchange, ticker (PK)
- stock_name, currency, quantity
- avg_purchase_price, current_price
- purchase_amount, eval_amount
- profit_loss_amount, profit_loss_rate

**daily_summary_records** (계좌 요약)
- record_date, exchange (PK)
- currency, total_purchase_amount, total_eval_amount
- total_profit_loss, total_profit_rate, stock_count

**recording_logs** (기록 로그)
- record_date (PK), status
- started_at, completed_at
- exchanges_processed, total_stocks, error_message

### 주요 메서드

| 메서드 | 설명 |
|--------|------|
| `save_stock_records(records)` | 종목 기록 저장 (upsert) |
| `save_summary_record(record)` | 요약 기록 저장 (upsert) |
| `get_stock_records(...)` | 종목 기록 조회 (페이징) |
| `get_summary_records(...)` | 요약 기록 조회 (페이징) |
| `get_stock_by_ticker(ticker, ...)` | 특정 종목 히스토리 |
| `get_latest_record_date()` | 최신 기록 날짜 |
| `get_latest_records()` | 최신 기록 데이터 |
| `compare_dates(date1, date2, exchange)` | 두 날짜 비교 |
| `create_recording_log(record_date)` | 기록 로그 생성 |
| `update_recording_log(...)` | 기록 로그 업데이트 |
| `get_recording_logs(limit)` | 기록 로그 조회 |

---

## 10. RedisService

**파일**: `app/services/redis_service.py`

### 역할
Redis 캐시 관리 (빠른 조회용)

### 키 구조

| 키 패턴 | 용도 | TTL |
|---------|------|-----|
| `mybutler:stock:{exchange}:{date}` | 종목 데이터 (Hash) | 설정값 |
| `mybutler:summary:{exchange}:{date}` | 요약 데이터 (String) | 설정값 |
| `mybutler:latest:{exchange}` | 최신 기록 날짜 | 없음 |
| `mybutler:recording:status` | 기록 작업 상태 (Hash) | 없음 |

### 주요 메서드

| 메서드 | 설명 |
|--------|------|
| `save_stock_records(exchange, date, stocks)` | 종목 데이터 저장 |
| `get_stock_records(exchange, date)` | 종목 데이터 조회 |
| `save_summary_record(exchange, date, summary)` | 요약 데이터 저장 |
| `get_summary_record(exchange, date)` | 요약 데이터 조회 |
| `set_latest_date(exchange, date)` | 최신 날짜 설정 |
| `get_latest_date(exchange)` | 최신 날짜 조회 |
| `set_recording_status(status)` | 기록 상태 저장 |
| `get_recording_status()` | 기록 상태 조회 |
| `clear_recording_status()` | 기록 상태 초기화 |

---

## 서비스 의존성 다이어그램

```
┌─────────────────────────────────────────────────────────────┐
│                     Controller Layer                         │
│  (screening_controller, history_controller)                  │
└─────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────┐
│                      Service Layer                           │
├─────────────────────────────────────────────────────────────┤
│                                                              │
│  ┌──────────────────┐    ┌──────────────────┐               │
│  │ ScreeningService │    │ RecordingService │               │
│  └────────┬─────────┘    └────────┬─────────┘               │
│           │                       │                          │
│           ▼                       ▼                          │
│  ┌──────────────────┐    ┌──────────────────┐               │
│  │ IchimokuService  │    │  BalanceService  │               │
│  └──────────────────┘    └──────────────────┘               │
│           │                       │                          │
│           ▼                       ▼                          │
│  ┌──────────────────┐    ┌──────────────────┐               │
│  │TechnicalService  │    │  HistoryService  │               │
│  │  ├─Bollinger     │    │    (SQLite)      │               │
│  │  ├─MAAlignment   │    └────────┬─────────┘               │
│  │  └─CupHandle     │             │                          │
│  └────────┬─────────┘             │                          │
│           │                       ▼                          │
│           ▼              ┌──────────────────┐               │
│  ┌──────────────────┐    │   RedisService   │               │
│  │ StockDataService │    │    (Cache)       │               │
│  │ (yfinance/pykrx) │    └──────────────────┘               │
│  └──────────────────┘                                        │
│                                                              │
└─────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────┐
│                      Data Layer                              │
│  (SQLite: daily_stock_records, daily_summary_records)        │
│  (Redis: 캐시 데이터)                                         │
│  (External: yfinance, pykrx, 한국투자증권 API)                │
└─────────────────────────────────────────────────────────────┘
```

---

## API 엔드포인트 요약

### 스크리닝 API (`/api/v1/screening`)

| 메서드 | 경로 | 설명 |
|--------|------|------|
| POST | `/run` | 통합 스크리닝 (필터 선택 가능) |
| GET | `/us` | 미국 주식 스크리닝 |
| GET | `/kr` | 한국 주식 스크리닝 |
| GET | `/perfect` | 일목균형표 완벽 조건 종목 |
| GET | `/bollinger-squeeze` | 볼린저 스퀴즈 스크리닝 |
| GET | `/ma-alignment` | 이평선 정배열 스크리닝 |
| GET | `/cup-and-handle` | 컵앤핸들 패턴 스크리닝 |
| GET | `/history` | 스크리닝 히스토리 조회 |
| GET | `/recommendations` | 최신 추천 종목 |
| GET | `/criteria` | 스크리닝 기준 정보 |

---

## 용어 정리

| 용어 | 설명 |
|------|------|
| OHLCV | Open, High, Low, Close, Volume |
| 구름대 | 선행스팬A와 선행스팬B 사이 영역 |
| 양운 | 선행스팬A > 선행스팬B (상승 추세) |
| 음운 | 선행스팬A < 선행스팬B (하락 추세) |
| 골든크로스 | 단기 이평선이 장기 이평선을 상향 돌파 |
| 데드크로스 | 단기 이평선이 장기 이평선을 하향 돌파 |
| 구름대 돌파 | 가격이 구름대 상단을 상향 돌파 |
| 스퀴즈 | 볼린저 밴드폭이 좁아진 상태 (에너지 응축) |
| 정배열 | 단기 이평선 > 장기 이평선 순서로 정렬된 상태 |
| 컵앤핸들 | U자형 바닥(컵) 후 작은 눌림(핸들) 패턴 |
| 이격도 | 현재가와 이동평균선 간의 괴리율 |
| %B | 볼린저 밴드 내 현재가 위치 (0~1) |
