# -*- coding: utf-8 -*-
"""
KIS Stock Data Service
한국투자증권 Open API 기반 주식 데이터 서비스
"""
import logging
import time
from datetime import datetime, timedelta
from functools import lru_cache
from typing import Dict, List, Optional

import pandas as pd

from app.utils.kis_auth_manager import get_auth_manager
from app.utils.kis_rate_limiter import get_rate_limiter

logger = logging.getLogger(__name__)


class KISStockDataService:
    """한국투자증권 API 기반 주식 데이터 서비스"""

    # API 엔드포인트
    KR_OHLCV_URL = "/uapi/domestic-stock/v1/quotations/inquire-daily-itemchartprice"
    US_OHLCV_URL = "/uapi/overseas-price/v1/quotations/dailyprice"
    KR_MARKET_CAP_URL = "/uapi/domestic-stock/v1/quotations/volume-rank"
    US_VOLUME_RANK_URL = "/uapi/overseas-price/v1/quotations/inquire-search"

    # TR ID
    KR_OHLCV_TR_ID = "FHKST03010100"
    US_OHLCV_TR_ID = "HHDFS76240000"
    KR_MARKET_CAP_TR_ID = "FHPST01710000"
    US_VOLUME_RANK_TR_ID = "HHDFS76410000"

    # 거래소 코드 매핑
    EXCHANGE_CODES = {
        "NASDAQ": "NAS",
        "NYSE": "NYS",
        "AMEX": "AMS",
        "NAS": "NAS",
        "NYS": "NYS",
        "AMS": "AMS",
    }

    def __init__(self):
        self.auth_manager = get_auth_manager()
        self.rate_limiter = get_rate_limiter()

    def get_kr_ohlcv(
        self,
        ticker: str,
        start_date: str = None,
        end_date: str = None,
        period_days: int = 200,
    ) -> Optional[pd.DataFrame]:
        """
        국내주식 OHLCV 데이터 조회

        Args:
            ticker: 종목코드 (예: 005930)
            start_date: 시작일 (YYYYMMDD), None이면 period_days로 계산
            end_date: 종료일 (YYYYMMDD), None이면 오늘
            period_days: 조회 기간 (일), start_date가 None일 때 사용

        Returns:
            DataFrame with columns: Open, High, Low, Close, Volume, Value
        """
        try:
            self.auth_manager.ensure_authenticated()

            # 날짜 계산
            if end_date is None:
                end_date = datetime.now().strftime("%Y%m%d")
            if start_date is None:
                start_dt = datetime.now() - timedelta(days=period_days + 30)
                start_date = start_dt.strftime("%Y%m%d")

            # 연속조회를 위한 변수
            all_data = []
            tr_cont = ""
            page = 1
            max_pages = 10

            while page <= max_pages:
                self.rate_limiter.wait_if_needed()

                params = {
                    "FID_COND_MRKT_DIV_CODE": "J",  # KRX
                    "FID_INPUT_ISCD": ticker,
                    "FID_INPUT_DATE_1": start_date,
                    "FID_INPUT_DATE_2": end_date,
                    "FID_PERIOD_DIV_CODE": "D",  # 일봉
                    "FID_ORG_ADJ_PRC": "0",  # 수정주가
                }

                result = self.auth_manager.api_call(
                    self.KR_OHLCV_URL, self.KR_OHLCV_TR_ID, params, tr_cont
                )

                if not result["success"]:
                    logger.warning(f"KIS API 호출 실패 (KR OHLCV {ticker}): {result.get('error')}")
                    break

                data = result["data"]
                headers = result["headers"]

                # output2: 일별 데이터
                output2 = data.get("output2", [])
                if output2:
                    all_data.extend(output2)
                    logger.debug(f"KR OHLCV {ticker}: 페이지 {page}, {len(output2)}건")

                # 연속조회 확인
                tr_cont = headers.get("tr_cont", "")
                if tr_cont in ["M", "F"]:
                    tr_cont = "N"
                    page += 1
                    self.rate_limiter.smart_sleep()
                else:
                    break

            if not all_data:
                return None

            # DataFrame 변환 및 정규화
            df = pd.DataFrame(all_data)
            df = self._normalize_kr_ohlcv(df)

            return df

        except Exception as e:
            logger.error(f"KIS KR OHLCV 조회 오류 ({ticker}): {e}")
            return None

    def _normalize_kr_ohlcv(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        국내주식 OHLCV 데이터 정규화

        KIS API 응답 필드:
        - stck_bsop_date: 영업일자
        - stck_oprc: 시가
        - stck_hgpr: 고가
        - stck_lwpr: 저가
        - stck_clpr: 종가
        - acml_vol: 누적거래량
        - acml_tr_pbmn: 누적거래대금
        """
        if df.empty:
            return df

        # 컬럼 매핑
        column_map = {
            "stck_bsop_date": "Date",
            "stck_oprc": "Open",
            "stck_hgpr": "High",
            "stck_lwpr": "Low",
            "stck_clpr": "Close",
            "acml_vol": "Volume",
            "acml_tr_pbmn": "Value",
        }

        # 필요한 컬럼만 선택
        available_cols = [c for c in column_map.keys() if c in df.columns]
        df = df[available_cols].rename(columns=column_map)

        # 숫자 변환
        for col in ["Open", "High", "Low", "Close", "Volume", "Value"]:
            if col in df.columns:
                df[col] = pd.to_numeric(df[col], errors="coerce")

        # 날짜 인덱스 설정
        if "Date" in df.columns:
            df["Date"] = pd.to_datetime(df["Date"], format="%Y%m%d")
            df = df.set_index("Date")
            df = df.sort_index()

        # 0 또는 빈 값 제거
        df = df[(df["Close"] > 0) & (df["Volume"] > 0)]

        return df[["Open", "High", "Low", "Close", "Volume", "Value"]]

    def get_us_ohlcv(
        self,
        ticker: str,
        exchange: str = None,
        period_days: int = 200,
        bymd: str = "",
    ) -> Optional[pd.DataFrame]:
        """
        해외주식 OHLCV 데이터 조회

        Args:
            ticker: 종목코드 (예: AAPL)
            exchange: 거래소 코드 (NAS, NYS, AMS), None이면 자동 추론
            period_days: 조회 기간 (일)
            bymd: 조회 기준일 (YYYYMMDD), 빈 문자열이면 최신

        Returns:
            DataFrame with columns: Open, High, Low, Close, Volume, Value
        """
        try:
            self.auth_manager.ensure_authenticated()

            # 거래소 코드 결정
            if exchange is None:
                exchange = self._guess_us_exchange(ticker)
            else:
                exchange = self.EXCHANGE_CODES.get(exchange.upper(), exchange)

            # 연속조회를 위한 변수
            all_data = []
            tr_cont = ""
            page = 1
            max_pages = 10
            current_bymd = bymd

            while page <= max_pages:
                self.rate_limiter.wait_if_needed()

                params = {
                    "AUTH": "",
                    "EXCD": exchange,
                    "SYMB": ticker,
                    "GUBN": "0",  # 일봉
                    "BYMD": current_bymd,
                    "MODP": "0",  # 수정주가
                }

                result = self.auth_manager.api_call(
                    self.US_OHLCV_URL, self.US_OHLCV_TR_ID, params, tr_cont
                )

                if not result["success"]:
                    logger.warning(f"KIS API 호출 실패 (US OHLCV {ticker}): {result.get('error')}")
                    break

                data = result["data"]
                headers = result["headers"]

                # output2: 일별 데이터
                output2 = data.get("output2", [])
                if output2:
                    all_data.extend(output2)
                    logger.debug(f"US OHLCV {ticker}: 페이지 {page}, {len(output2)}건")

                    # 충분한 데이터를 모았는지 확인
                    if len(all_data) >= period_days:
                        break

                # 연속조회 확인
                tr_cont = headers.get("tr_cont", "")
                if tr_cont in ["M", "F"]:
                    # 마지막 날짜를 다음 조회 기준일로 설정
                    if output2:
                        last_date = output2[-1].get("xymd", "")
                        if last_date:
                            current_bymd = last_date
                    tr_cont = "N"
                    page += 1
                    self.rate_limiter.smart_sleep()
                else:
                    break

            if not all_data:
                return None

            # DataFrame 변환 및 정규화
            df = pd.DataFrame(all_data)
            df = self._normalize_us_ohlcv(df)

            return df

        except Exception as e:
            logger.error(f"KIS US OHLCV 조회 오류 ({ticker}): {e}")
            return None

    def _normalize_us_ohlcv(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        해외주식 OHLCV 데이터 정규화

        KIS API 응답 필드:
        - xymd: 일자 (YYYYMMDD)
        - open: 시가
        - high: 고가
        - low: 저가
        - clos: 종가
        - tvol: 거래량
        - tamt: 거래대금 (없을 수 있음)
        """
        if df.empty:
            return df

        # 컬럼 매핑
        column_map = {
            "xymd": "Date",
            "open": "Open",
            "high": "High",
            "low": "Low",
            "clos": "Close",
            "tvol": "Volume",
        }

        # 필요한 컬럼만 선택
        available_cols = [c for c in column_map.keys() if c in df.columns]
        df = df[available_cols].rename(columns=column_map)

        # 숫자 변환
        for col in ["Open", "High", "Low", "Close", "Volume"]:
            if col in df.columns:
                df[col] = pd.to_numeric(df[col], errors="coerce")

        # Value 계산 (tamt가 없으면 Close * Volume)
        if "tamt" in df.columns:
            df["Value"] = pd.to_numeric(df["tamt"], errors="coerce")
        else:
            df["Value"] = df["Close"] * df["Volume"]

        # 날짜 인덱스 설정
        if "Date" in df.columns:
            df["Date"] = pd.to_datetime(df["Date"], format="%Y%m%d")
            df = df.set_index("Date")
            df = df.sort_index()

        # 0 또는 빈 값 제거
        df = df[(df["Close"] > 0) & (df["Volume"] > 0)]

        return df[["Open", "High", "Low", "Close", "Volume", "Value"]]

    def _guess_us_exchange(self, ticker: str) -> str:
        """
        종목코드로 거래소 추론

        대부분의 기술주는 NASDAQ, 전통 대형주는 NYSE
        """
        # 주요 NASDAQ 종목
        nasdaq_tickers = {
            "AAPL", "MSFT", "GOOGL", "GOOG", "AMZN", "NVDA", "META", "TSLA",
            "AVGO", "COST", "NFLX", "ADBE", "AMD", "INTC", "QCOM", "TXN",
            "CSCO", "CMCSA", "PEP", "TMUS", "AMGN", "SBUX", "ISRG", "INTU",
            "BKNG", "GILD", "MDLZ", "ADI", "REGN", "VRTX", "LRCX", "ASML",
            "SNPS", "CDNS", "KLAC", "MRVL", "FTNT", "PANW", "ABNB", "DXCM",
            "IDXX", "ILMN", "ALGN", "ENPH", "MELI", "WDAY", "PYPL", "ADP",
            "MU", "AMAT", "ORLY", "PCAR", "MCHP", "PAYX", "KDP", "AZN",
            "MRNA", "BIIB", "MNST", "KHC", "CTAS", "ROST", "EXC", "XEL",
            "EA", "WBD", "ODFL", "FAST", "EBAY", "DDOG", "ZS", "CRWD",
        }

        if ticker.upper() in nasdaq_tickers:
            return "NAS"

        # 기본값은 NYSE
        return "NYS"

    def get_kr_market_cap_stocks(self, market: str = "ALL", limit: int = 500) -> List[Dict]:
        """
        국내 시가총액 상위 종목 조회

        Args:
            market: KOSPI, KOSDAQ, ALL
            limit: 최대 종목 수

        Returns:
            List of {"ticker": str, "name": str, "market": str}
        """
        try:
            self.auth_manager.ensure_authenticated()
            self.rate_limiter.wait_if_needed()

            # 시장 코드 매핑
            if market == "KOSPI":
                mrkt_div_code = "J"
            elif market == "KOSDAQ":
                mrkt_div_code = "K"
            else:
                mrkt_div_code = "J"  # 전체는 KOSPI 기준

            params = {
                "FID_COND_MRKT_DIV_CODE": mrkt_div_code,
                "FID_COND_SCR_DIV_CODE": "20101",  # 거래량 상위
                "FID_INPUT_ISCD": "0000",  # 전체
                "FID_DIV_CLS_CODE": "0",
                "FID_BLNG_CLS_CODE": "0",
                "FID_TRGT_CLS_CODE": "111111111",
                "FID_TRGT_EXLS_CLS_CODE": "000000",
                "FID_INPUT_PRICE_1": "0",
                "FID_INPUT_PRICE_2": "0",
                "FID_VOL_CNT": "0",
                "FID_INPUT_DATE_1": "",
            }

            result = self.auth_manager.api_call(
                self.KR_MARKET_CAP_URL, self.KR_MARKET_CAP_TR_ID, params, ""
            )

            if not result["success"]:
                logger.warning(f"KIS API 호출 실패 (KR Market Cap): {result.get('error')}")
                return []

            output = result["data"].get("output", [])
            stocks = []

            for item in output[:limit]:
                ticker = item.get("mksc_shrn_iscd", "")  # 단축코드
                name = item.get("hts_kor_isnm", "")  # 종목명

                if not ticker:
                    continue

                # 시장 구분
                stock_market = "KOSPI" if ticker[0] in "0123" else "KOSDAQ"

                if market == "ALL" or market == stock_market:
                    stocks.append({
                        "ticker": ticker,
                        "name": name,
                        "market": stock_market,
                    })

            logger.info(f"KR 시가총액 상위 종목 조회: {len(stocks)}개")
            return stocks

        except Exception as e:
            logger.error(f"KIS KR Market Cap 조회 오류: {e}")
            return []

    def get_us_volume_rank_stocks(self, exchange: str = "NAS", limit: int = 200) -> List[Dict]:
        """
        미국 거래량 상위 종목 조회

        Args:
            exchange: NAS (NASDAQ), NYS (NYSE), AMS (AMEX)
            limit: 최대 종목 수

        Returns:
            List of {"ticker": str, "name": str, "market": str}
        """
        try:
            self.auth_manager.ensure_authenticated()
            self.rate_limiter.wait_if_needed()

            exchange_code = self.EXCHANGE_CODES.get(exchange.upper(), exchange)

            params = {
                "AUTH": "",
                "EXCD": exchange_code,
                "CO_YN_PRICECUR": "",
                "CO_ST_PRICECUR": "",
                "CO_EN_PRICECUR": "",
                "CO_YN_RATE": "",
                "CO_ST_RATE": "",
                "CO_EN_RATE": "",
                "CO_YN_VALX": "",
                "CO_ST_VALX": "",
                "CO_EN_VALX": "",
                "CO_YN_SHAR": "",
                "CO_ST_SHAR": "",
                "CO_EN_SHAR": "",
                "CO_YN_VOLUME": "",
                "CO_ST_VOLUME": "",
                "CO_EN_VOLUME": "",
                "CO_YN_AMT": "",
                "CO_ST_AMT": "",
                "CO_EN_AMT": "",
                "CO_YN_EPS": "",
                "CO_ST_EPS": "",
                "CO_EN_EPS": "",
                "CO_YN_PER": "",
                "CO_ST_PER": "",
                "CO_EN_PER": "",
            }

            result = self.auth_manager.api_call(
                self.US_VOLUME_RANK_URL, self.US_VOLUME_RANK_TR_ID, params, ""
            )

            if not result["success"]:
                logger.warning(f"KIS API 호출 실패 (US Volume Rank): {result.get('error')}")
                return []

            output = result["data"].get("output2", [])
            stocks = []

            # 마켓 이름 매핑
            market_name = {
                "NAS": "NASDAQ",
                "NYS": "NYSE",
                "AMS": "AMEX",
            }.get(exchange_code, "US")

            for item in output[:limit]:
                ticker = item.get("symb", "")  # 종목코드
                name = item.get("name", "")  # 종목명

                if not ticker:
                    continue

                stocks.append({
                    "ticker": ticker,
                    "name": name,
                    "market": market_name,
                })

            logger.info(f"US {market_name} 거래량 상위 종목 조회: {len(stocks)}개")
            return stocks

        except Exception as e:
            logger.error(f"KIS US Volume Rank 조회 오류: {e}")
            return []

    def get_all_us_stocks(self, limit_per_exchange: int = 100) -> List[Dict]:
        """
        모든 미국 거래소의 거래량 상위 종목 조회

        Args:
            limit_per_exchange: 거래소별 최대 종목 수

        Returns:
            List of {"ticker": str, "name": str, "market": str}
        """
        all_stocks = []

        for exchange in ["NAS", "NYS", "AMS"]:
            try:
                stocks = self.get_us_volume_rank_stocks(exchange, limit_per_exchange)
                all_stocks.extend(stocks)
                self.rate_limiter.smart_sleep()
            except Exception as e:
                logger.warning(f"{exchange} 종목 조회 실패: {e}")
                continue

        # 중복 제거 (ticker 기준)
        seen = set()
        unique_stocks = []
        for s in all_stocks:
            if s["ticker"] not in seen:
                seen.add(s["ticker"])
                unique_stocks.append(s)

        logger.info(f"US 전체 거래량 상위 종목: {len(unique_stocks)}개")
        return unique_stocks


@lru_cache()
def get_kis_stock_data_service() -> KISStockDataService:
    """KIS Stock Data Service 싱글톤"""
    return KISStockDataService()
