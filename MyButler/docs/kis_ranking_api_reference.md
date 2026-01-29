# 한국투자증권 Open API - 순위/분석 API 레퍼런스

## 개요

한국투자증권 Open API에서 제공하는 순위 분석, 시세 분석 관련 API 목록입니다.
급등주, 거래량 상위, 투자자별 매매동향 등 다양한 분석 데이터를 조회할 수 있습니다.

---

## 1. 국내주식 순위분석 API

### 1.1 등락률 순위 (fluctuation)

| 항목 | 내용 |
|------|------|
| API 경로 | `/uapi/domestic-stock/v1/ranking/fluctuation` |
| TR ID | `FHPST01700000` |
| 기능 | 상승률/하락률 기준 종목 순위 |

**주요 파라미터:**
- `fid_cond_mrkt_div_code`: 시장구분 (J=KRX, NX=NXT)
- `fid_cond_scr_div_code`: 화면분류코드 (20170: 등락률)
- `fid_input_iscd`: 종목코드 (0000=전체)
- `fid_rank_sort_cls_code`: 순위정렬구분 (0000=등락률순)
- `fid_rsfl_rate1`: 하락률 하한
- `fid_rsfl_rate2`: 상승률 상한
- `fid_vol_cnt`: 최소 거래량

```python
df = fluctuation(
    fid_cond_mrkt_div_code="J",
    fid_cond_scr_div_code="20170",
    fid_input_iscd="0000",
    fid_rank_sort_cls_code="0000",
    fid_input_cnt_1="10",
    fid_rsfl_rate2="10"
)
```

---

### 1.2 거래량 순위 (volume_rank)

| 항목 | 내용 |
|------|------|
| API 경로 | `/uapi/domestic-stock/v1/quotations/volume-rank` |
| TR ID | `FHPST01710000` |
| 기능 | 거래량 기준 순위 조회 |

**주요 파라미터:**
- `fid_cond_mrkt_div_code`: 시장구분 (J=KRX, NX=NXT, UN=통합, W=ELW)
- `fid_cond_scr_div_code`: 화면분류코드 (20171)
- `fid_input_iscd`: 종목코드 (0000=전체, 기타=업종코드)
- `fid_div_cls_code`: 분류구분 (0=전체, 1=보통주, 2=우선주)
- `fid_blng_cls_code`: 소속구분
  - 0: 평균거래량
  - 1: 거래증가율
  - 2: 평균거래회전율
  - 3: 거래금액순
  - 4: 평균거래금액회전율

```python
df = volume_rank(
    fid_cond_mrkt_div_code="J",
    fid_cond_scr_div_code="20171",
    fid_input_iscd="0000",
    fid_div_cls_code="0",
    fid_blng_cls_code="0",
    fid_trgt_cls_code="111111111",
    fid_trgt_exls_cls_code="0000000000",
    fid_input_price_1="0",
    fid_input_price_2="1000000",
    fid_vol_cnt="100000",
    fid_input_date_1=""
)
```

---

### 1.3 시가총액 상위 (market_cap)

| 항목 | 내용 |
|------|------|
| API 경로 | `/uapi/domestic-stock/v1/ranking/market-cap` |
| TR ID | `FHPST01740000` |
| 기능 | 시가총액 기준 상위 종목 |

**주요 파라미터:**
- `fid_cond_mrkt_div_code`: 시장구분 (J=KRX, NX=NXT)
- `fid_cond_scr_div_code`: 화면분류코드 (20174)
- `fid_input_iscd`: 종목코드
  - 0000: 전체
  - 0001: 거래소(KOSPI)
  - 1001: 코스닥
  - 2001: 코스피200
- `fid_div_cls_code`: 분류구분 (0=전체, 1=보통주, 2=우선주)

```python
df = market_cap(
    fid_input_price_2="",
    fid_cond_mrkt_div_code="J",
    fid_cond_scr_div_code="20174",
    fid_div_cls_code="0",
    fid_input_iscd="0000"
)
```

---

### 1.4 체결강도 상위 (volume_power)

| 항목 | 내용 |
|------|------|
| API 경로 | `/uapi/domestic-stock/v1/ranking/volume-power` |
| TR ID | `FHPST01680000` |
| 기능 | 체결강도 기준 상위 종목 |

**주요 파라미터:**
- `fid_cond_mrkt_div_code`: 시장구분 (J=KRX, NX=NXT)
- `fid_cond_scr_div_code`: 화면분류코드 (20168)
- `fid_input_iscd`: 종목코드 (0000=전체, 0001=거래소, 1001=코스닥, 2001=코스피200)
- `fid_div_cls_code`: 분류구분 (0=전체, 1=보통주, 2=우선주)

---

### 1.5 상하한가 포착 (capture_uplowprice)

| 항목 | 내용 |
|------|------|
| API 경로 | `/uapi/domestic-stock/v1/quotations/capture-uplowprice` |
| TR ID | `FHKST130000C0` |
| 기능 | 상한가/하한가 근접 종목 검색 |

**주요 파라미터:**
- `fid_prc_cls_code`: 가격구분 (0=상한가, 1=하한가)
- `fid_div_cls_code`: 근접율 구분
  - 0: 상하한가 종목
  - 6: 8% 근접
  - 5: 10% 근접
  - 1: 15% 근접
  - 2: 20% 근접
  - 3: 25% 근접
- `fid_input_iscd`: 종목코드 (0000=전체, 0001=코스피, 1001=코스닥)

```python
# 상한가 8% 근접 종목 조회
df = capture_uplowprice("J", "11300", "0", "6", "0000")
```

---

### 1.6 52주 신고가/신저가 근접 (near_new_highlow)

| 항목 | 내용 |
|------|------|
| API 경로 | `/uapi/domestic-stock/v1/ranking/near-new-highlow` |
| TR ID | `FHPST01870000` |
| 기능 | 52주 신고가/신저가 근접 종목 |

**주요 파라미터:**
- `fid_prc_cls_code`: 구분 (0=신고가근접, 1=신저가근접)
- `fid_input_cnt_1`, `fid_input_cnt_2`: 괴리율 범위

---

### 1.7 HTS 조회상위 (hts_top_view)

| 항목 | 내용 |
|------|------|
| API 경로 | `/uapi/domestic-stock/v1/ranking/hts-top-view` |
| TR ID | `HHMCM000100C0` |
| 기능 | HTS에서 가장 많이 조회된 상위 20종목 |

```python
# 파라미터 없음
df = hts_top_view()
```

---

## 2. 투자자 매매동향 API

### 2.1 주식현재가 투자자 (inquire_investor)

| 항목 | 내용 |
|------|------|
| API 경로 | `/uapi/domestic-stock/v1/quotations/inquire-investor` |
| TR ID | `FHKST01010900` |
| 기능 | 개별 종목의 투자자별 매매 정보 |

```python
df = inquire_investor(
    env_dv="real",
    fid_cond_mrkt_div_code="J",
    fid_input_iscd="005930"  # 삼성전자
)
```

---

### 2.2 외인/기관 매매종목 종합 (foreign_institution_total)

| 항목 | 내용 |
|------|------|
| API 경로 | `/uapi/domestic-stock/v1/quotations/foreign-institution-total` |
| TR ID | `FHPTJ04400000` |
| 기능 | 기관, 외국인 매매종목 종합 집계 |

**주요 파라미터:**
- `fid_rank_sort_cls_code`: 순위정렬 (0=순매수상위, 1=순매도상위)
- `fid_etc_cls_code`: 기타구분 (0=전체, 1=외국인, 2=기관계, 3=기타)
- `fid_div_cls_code`: 정렬기준 (0=수량정렬, 1=금액정렬)

```python
df = foreign_institution_total("V", "16449", "0000", "0", "0", "0")
```

---

### 2.3 기타 투자자 관련 API

| API 메서드 | 설명 |
|-----------|------|
| `investor_trend_estimate` | 종목별 외인/기관 추정가집계 |
| `inquire_investor_time_by_market` | 시장별 투자자매매동향(시세) |
| `inquire_investor_daily_by_market` | 시장별 투자자매매동향(일별) |
| `investor_program_trade_today` | 프로그램매매 투자자매매동향(당일) |
| `investor_trade_by_stock_daily` | 종목별 투자자매매동향(일별) |

---

## 3. 해외주식 순위분석 API

### 3.1 상승율/하락율 (updown_rate)

| 항목 | 내용 |
|------|------|
| API 경로 | `/uapi/overseas-stock/v1/ranking/updown-rate` |
| 기능 | 해외주식 상승율/하락율 순위 |

**주요 파라미터:**
- `excd`: 거래소명
  - NYS: 뉴욕
  - NAS: 나스닥
  - AMS: 아멕스
  - HKS: 홍콩
  - SHS: 상해
  - SZS: 심천
  - HSX: 호치민
  - HNX: 하노이
  - TSE: 도쿄
- `nday`: N일자값 (0=당일, 1=2일, ... 9=1년)
- `gubn`: 구분 (0=하락율, 1=상승율)
- `vol_rang`: 거래량조건 (0=전체, 1=1백주이상, ... 6=1000만주이상)

---

### 3.2 가격 급등락 (price_fluct)

| 항목 | 내용 |
|------|------|
| API 경로 | `/uapi/overseas-stock/v1/ranking/price-fluct` |
| 기능 | 해외주식 가격 급등/급락 |

**주요 파라미터:**
- `excd`: 거래소명
- `gubn`: 구분 (0=급락, 1=급등)
- `mixn`: N분전 콤보값 (0=1분전, 1=2분전, ... 9=120분전)
- `vol_rang`: 거래량조건

---

### 3.3 거래량 순위 (trade_vol)

| 항목 | 내용 |
|------|------|
| API 경로 | `/uapi/overseas-stock/v1/ranking/trade-vol` |
| 기능 | 해외주식 거래량 순위 |

**주요 파라미터:**
- `excd`: 거래소명
- `nday`: N일전 콤보값
- `vol_rang`: 거래량조건

---

## 4. 기타 유용한 API

| API 메서드 | 설명 |
|-----------|------|
| `dividend_rate` | 배당률 순위 |
| `bulk_trans_num` | 대량거래 건수 |
| `short_sale` | 공매도 정보 |
| `after_hour_balance` | 시간외 거래 순위 |
| `program_trade_krx` | 프로그램 매매 현황 |
| `top_interest_stock` | 상위 관심 종목 |
| `inquire_member_daily` | 회원사별 일일 거래 |

---

## 5. 공통 필터 조건

### 5.1 시장 구분 코드 (fid_input_iscd)
| 코드 | 설명 |
|------|------|
| 0000 | 전체 |
| 0001 | 거래소 (KOSPI) |
| 1001 | 코스닥 |
| 2001 | 코스피200 |

### 5.2 대상 제외 구분 코드 (fid_trgt_exls_cls_code)
10자리 문자열, 각 자리 "1"=제외, "0"=포함:
1. 투자위험/경고/주의
2. 관리종목
3. 정리매매
4. 불성실공시
5. 우선주
6. 거래정지
7. ETF
8. ETN
9. 신용주문불가
10. SPAC

---

## 6. API 호출 기본 구조

```python
import kis_auth as ka
import pandas as pd

# 인증
ka.auth(svr="prod")  # prod=실전, vps=모의투자

# API 호출
res = ka._url_fetch(API_URL, TR_ID, tr_cont, params)

# 응답 처리
if res.isOK():
    df = pd.DataFrame(res.getBody().output)
else:
    res.printError(url=API_URL)
```

---

## 7. 참고 링크

- GitHub: https://github.com/koreainvestment/open-trading-api
- 레퍼런스 프로젝트 위치: `References_Project/open-trading-api-main/`
- 예제 코드: `examples_llm/domestic_stock/` (API별 독립 폴더)
