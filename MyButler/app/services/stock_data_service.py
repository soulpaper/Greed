# -*- coding: utf-8 -*-
"""
Stock Data Service
주식 데이터 수집 서비스 (KIS API 우선 + yfinance/pykrx fallback)
"""
import logging
from datetime import datetime, timedelta, date
from typing import List, Dict, Any, Optional, Tuple
from concurrent.futures import ThreadPoolExecutor, as_completed

import pandas as pd
import numpy as np

logger = logging.getLogger(__name__)


class StockDataService:
    """
    주식 데이터 수집 서비스

    데이터 소스 우선순위:
    1. KIS API (한국투자증권 Open API)
    2. Fallback: yfinance (해외), pykrx (국내)
    """

    # 거래대금 기준 (원화, 달러)
    KR_MIN_TRADING_VALUE = 5_000_000_000  # 50억원
    US_MIN_TRADING_VALUE = 20_000_000  # $20M

    def __init__(self, use_kis: bool = True, use_fallback: bool = True):
        """
        초기화

        Args:
            use_kis: KIS API 사용 여부
            use_fallback: fallback (yfinance, pykrx) 사용 여부
        """
        self.use_kis = use_kis
        self.use_fallback = use_fallback

        # KIS 서비스 (lazy load)
        self._kis_service = None

        # Fallback 서비스 (lazy load)
        self._yf = None
        self._pykrx_stock = None

    @property
    def kis_service(self):
        """KIS Stock Data Service lazy load"""
        if self._kis_service is None:
            try:
                from app.services.kis_stock_data_service import get_kis_stock_data_service
                self._kis_service = get_kis_stock_data_service()
            except Exception as e:
                logger.warning(f"KIS 서비스 로드 실패: {e}")
                self._kis_service = None
        return self._kis_service

    @property
    def yf(self):
        """yfinance lazy import"""
        if self._yf is None:
            import yfinance as yf
            self._yf = yf
        return self._yf

    @property
    def pykrx_stock(self):
        """pykrx lazy import"""
        if self._pykrx_stock is None:
            from pykrx import stock
            self._pykrx_stock = stock
        return self._pykrx_stock

    # 미국 주식 목록 캐시
    _us_stocks_cache: List[str] = None
    _us_stocks_cache_date: date = None

    def _fetch_sp500_from_wikipedia(self) -> List[str]:
        """Wikipedia에서 S&P 500 종목 목록 가져오기"""
        try:
            import pandas as pd
            url = "https://en.wikipedia.org/wiki/List_of_S%26P_500_companies"
            tables = pd.read_html(url)
            sp500_df = tables[0]
            tickers = sp500_df['Symbol'].tolist()
            # BRK.B -> BRK-B 형식 변환 (yfinance 호환)
            tickers = [t.replace('.', '-') for t in tickers]
            logger.info(f"S&P 500 목록 조회 완료: {len(tickers)}개")
            return tickers
        except Exception as e:
            logger.warning(f"Wikipedia S&P 500 조회 실패: {e}")
            return []

    def _fetch_nasdaq100_from_wikipedia(self) -> List[str]:
        """Wikipedia에서 NASDAQ 100 종목 목록 가져오기"""
        try:
            import pandas as pd
            url = "https://en.wikipedia.org/wiki/Nasdaq-100"
            tables = pd.read_html(url)
            # NASDAQ 100 테이블 찾기 (Ticker 컬럼이 있는 테이블)
            for table in tables:
                if 'Ticker' in table.columns:
                    tickers = table['Ticker'].tolist()
                    tickers = [t.replace('.', '-') for t in tickers]
                    logger.info(f"NASDAQ 100 목록 조회 완료: {len(tickers)}개")
                    return tickers
            logger.warning("NASDAQ 100 테이블을 찾을 수 없음")
            return []
        except Exception as e:
            logger.warning(f"Wikipedia NASDAQ 100 조회 실패: {e}")
            return []

    def get_us_stock_list(self) -> List[Dict[str, str]]:
        """
        미국 주식 목록 가져오기

        데이터 소스 우선순위:
        1. KIS API 거래량 상위 종목
        2. Wikipedia S&P 500 + NASDAQ 100
        3. Fallback 하드코딩 목록
        """
        today = datetime.now().date()

        # 캐시 확인 (당일 캐시 유효)
        if self._us_stocks_cache and self._us_stocks_cache_date == today:
            return [{"ticker": t, "market": "US"} for t in self._us_stocks_cache]

        # 1. KIS API 시도
        if self.use_kis and self.kis_service:
            try:
                stocks = self.kis_service.get_all_us_stocks(limit_per_exchange=150)
                if stocks:
                    tickers = [s["ticker"] for s in stocks]
                    StockDataService._us_stocks_cache = tickers
                    StockDataService._us_stocks_cache_date = today
                    logger.info(f"KIS API 미국 주식 목록: {len(tickers)}개")
                    return stocks
            except Exception as e:
                logger.warning(f"KIS API 미국 주식 목록 조회 실패: {e}")

        # 2. Fallback: Wikipedia에서 조회
        if self.use_fallback:
            sp500 = self._fetch_sp500_from_wikipedia()
            nasdaq100 = self._fetch_nasdaq100_from_wikipedia()

            # 중복 제거하여 합치기
            all_tickers = list(set(sp500 + nasdaq100))

            if all_tickers:
                # 캐시 갱신
                StockDataService._us_stocks_cache = all_tickers
                StockDataService._us_stocks_cache_date = today
                logger.info(f"Wikipedia 미국 주식 목록: S&P500({len(sp500)}) + NASDAQ100({len(nasdaq100)}) = {len(all_tickers)}개")
                return [{"ticker": t, "market": "US"} for t in all_tickers]

        # 3. Fallback: 주요 종목 목록
        logger.warning("미국 주식 목록 조회 실패, fallback 목록 사용")
        fallback_tickers = [
            "AAPL", "MSFT", "GOOGL", "GOOG", "AMZN", "NVDA", "META", "TSLA", "BRK-B",
            "UNH", "JNJ", "XOM", "JPM", "V", "PG", "MA", "HD", "CVX", "MRK", "ABBV",
            "LLY", "PEP", "KO", "COST", "AVGO", "WMT", "MCD", "CSCO", "ACN", "TMO",
            "ABT", "DHR", "NEE", "LIN", "ADBE", "NKE", "CRM", "TXN", "PM", "VZ",
            "CMCSA", "ORCL", "AMD", "INTC", "QCOM", "HON", "UNP", "IBM", "AMGN", "RTX",
            "NFLX", "PYPL", "INTU", "ISRG", "SBUX", "BKNG", "GILD", "MDLZ", "ADI",
            "REGN", "VRTX", "LRCX", "ASML", "SNPS", "CDNS", "KLAC", "MRVL", "FTNT",
            "PANW", "ABNB", "DXCM", "IDXX", "ILMN", "ALGN", "ENPH", "MELI", "WDAY",
        ]
        return [{"ticker": t, "market": "US"} for t in fallback_tickers]

    # 한국 주요 지수 코드
    KR_INDEX_CODES = {
        "KOSPI200": "1028",
        "KOSPI150": "1034",
        "KRX300": "1005",
    }

    def get_kr_stock_list(self, market: str = "ALL") -> List[Dict[str, str]]:
        """
        한국 주식 목록 가져오기

        데이터 소스 우선순위:
        1. KIS API 시가총액/거래량 상위 종목
        2. pykrx 지수 구성 종목

        Args:
            market: KOSPI, KOSDAQ, ALL

        Returns:
            List of {"ticker": str, "name": str, "market": str}
        """
        # 1. KIS API 시도
        if self.use_kis and self.kis_service:
            try:
                stocks = self.kis_service.get_kr_market_cap_stocks(market=market, limit=500)
                if stocks:
                    logger.info(f"KIS API 한국 주식 목록: {len(stocks)}개")
                    return stocks
            except Exception as e:
                logger.warning(f"KIS API 한국 주식 목록 조회 실패: {e}")

        # 2. Fallback: pykrx
        if self.use_fallback:
            return self._get_kr_stock_list_pykrx(market)

        return []

    def _get_kr_stock_list_pykrx(self, market: str = "ALL") -> List[Dict[str, str]]:
        """
        pykrx를 사용한 한국 주식 목록 가져오기 (fallback)

        Args:
            market: KOSPI, KOSDAQ, ALL (지수 구성 종목 중 필터링)

        Returns:
            코스피200 + 코스피150 + KRX300 구성 종목 (중복 제거)
        """
        try:
            today = datetime.now().strftime("%Y%m%d")

            # 지수 구성 종목 수집 (중복 제거)
            ticker_set = set()

            for index_name, index_code in self.KR_INDEX_CODES.items():
                try:
                    index_tickers = self.pykrx_stock.get_index_portfolio_deposit_file(index_code, today)
                    if index_tickers is not None:
                        ticker_set.update(index_tickers)
                        logger.info(f"{index_name} 구성 종목: {len(index_tickers)}개")
                except Exception as e:
                    logger.warning(f"{index_name} 조회 실패: {e}")

            # 종목 정보 조회
            tickers = []
            for t in ticker_set:
                try:
                    name = self.pykrx_stock.get_market_ticker_name(t)
                    # 시장 구분 (6자리 코드 기준: 0~3으로 시작하면 KOSPI)
                    stock_market = "KOSPI" if t[0] in "0123" else "KOSDAQ"

                    # 시장 필터링
                    if market == "ALL" or market == stock_market:
                        tickers.append({"ticker": t, "name": name, "market": stock_market})
                except Exception:
                    continue

            logger.info(f"pykrx 한국 주식 목록 조회 완료: {len(tickers)}개 (지수 구성 종목)")
            return tickers

        except Exception as e:
            logger.error(f"pykrx 한국 주식 목록 조회 실패: {e}")
            return []

    def get_us_ohlcv(
        self,
        ticker: str,
        period_days: int = 200
    ) -> Optional[pd.DataFrame]:
        """
        미국 주식 OHLCV 데이터 가져오기

        데이터 소스 우선순위:
        1. KIS API
        2. yfinance (fallback)

        Returns:
            DataFrame with columns: Open, High, Low, Close, Volume, Value
        """
        # 1. KIS API 시도
        if self.use_kis and self.kis_service:
            try:
                df = self.kis_service.get_us_ohlcv(ticker, period_days=period_days)
                if df is not None and not df.empty:
                    logger.debug(f"KIS API US OHLCV {ticker}: {len(df)}건")
                    return self._normalize_ohlcv(df)
            except Exception as e:
                logger.debug(f"KIS API US OHLCV {ticker} 실패: {e}")

        # 2. Fallback: yfinance
        if self.use_fallback:
            return self._get_us_ohlcv_yfinance(ticker, period_days)

        return None

    def _get_us_ohlcv_yfinance(
        self,
        ticker: str,
        period_days: int = 200
    ) -> Optional[pd.DataFrame]:
        """
        yfinance를 사용한 미국 주식 OHLCV 데이터 (fallback)

        Returns:
            DataFrame with columns: Open, High, Low, Close, Volume, Value
        """
        try:
            end_date = datetime.now()
            start_date = end_date - timedelta(days=period_days + 30)  # 여유분 추가

            stock = self.yf.Ticker(ticker)
            df = stock.history(start=start_date, end=end_date)

            if df.empty:
                return None

            # 거래대금 계산 (Close * Volume)
            df["Value"] = df["Close"] * df["Volume"]

            # 컬럼 정리
            df = df[["Open", "High", "Low", "Close", "Volume", "Value"]]

            return df

        except Exception as e:
            logger.debug(f"yfinance 미국 주식 {ticker} 데이터 조회 실패: {e}")
            return None

    def get_kr_ohlcv(
        self,
        ticker: str,
        period_days: int = 200
    ) -> Optional[pd.DataFrame]:
        """
        한국 주식 OHLCV 데이터 가져오기

        데이터 소스 우선순위:
        1. KIS API
        2. pykrx (fallback)

        Returns:
            DataFrame with columns: Open, High, Low, Close, Volume, Value
        """
        # 1. KIS API 시도
        if self.use_kis and self.kis_service:
            try:
                df = self.kis_service.get_kr_ohlcv(ticker, period_days=period_days)
                if df is not None and not df.empty:
                    logger.debug(f"KIS API KR OHLCV {ticker}: {len(df)}건")
                    return self._normalize_ohlcv(df)
            except Exception as e:
                logger.debug(f"KIS API KR OHLCV {ticker} 실패: {e}")

        # 2. Fallback: pykrx
        if self.use_fallback:
            return self._get_kr_ohlcv_pykrx(ticker, period_days)

        return None

    def _get_kr_ohlcv_pykrx(
        self,
        ticker: str,
        period_days: int = 200
    ) -> Optional[pd.DataFrame]:
        """
        pykrx를 사용한 한국 주식 OHLCV 데이터 (fallback)

        Returns:
            DataFrame with columns: Open, High, Low, Close, Volume, Value
        """
        try:
            end_date = datetime.now().strftime("%Y%m%d")
            start_date = (datetime.now() - timedelta(days=period_days + 30)).strftime("%Y%m%d")

            df = self.pykrx_stock.get_market_ohlcv_by_date(start_date, end_date, ticker)

            if df.empty:
                return None

            # 컬럼명 영문으로 변환
            df = df.rename(columns={
                "시가": "Open",
                "고가": "High",
                "저가": "Low",
                "종가": "Close",
                "거래량": "Volume",
                "거래대금": "Value"
            })

            return df[["Open", "High", "Low", "Close", "Volume", "Value"]]

        except Exception as e:
            logger.debug(f"pykrx 한국 주식 {ticker} 데이터 조회 실패: {e}")
            return None

    def _normalize_ohlcv(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        OHLCV DataFrame 정규화

        - 필수 컬럼 존재 확인
        - 숫자 타입 변환
        - 유효 데이터만 필터링

        Args:
            df: 원본 DataFrame

        Returns:
            정규화된 DataFrame
        """
        if df is None or df.empty:
            return df

        required_cols = ["Open", "High", "Low", "Close", "Volume", "Value"]

        # 필수 컬럼 확인
        for col in required_cols:
            if col not in df.columns:
                logger.warning(f"OHLCV 정규화 실패: {col} 컬럼 누락")
                return df

        # 숫자 타입 변환
        for col in required_cols:
            df[col] = pd.to_numeric(df[col], errors="coerce")

        # 유효 데이터 필터 (종가 > 0, 거래량 > 0)
        df = df[(df["Close"] > 0) & (df["Volume"] > 0)]

        return df[required_cols]

    def filter_by_trading_value(
        self,
        df: pd.DataFrame,
        min_value: float,
        avg_days: int = 5
    ) -> bool:
        """
        거래대금 기준 필터링

        Args:
            df: OHLCV 데이터
            min_value: 최소 거래대금
            avg_days: 평균 계산 일수

        Returns:
            True if 기준 충족
        """
        if df is None or len(df) < avg_days:
            return False

        recent_df = df.tail(avg_days)
        avg_value = recent_df["Value"].mean()

        return avg_value >= min_value

    def get_filtered_us_stocks(
        self,
        min_trading_value: float = None,
        max_workers: int = 10
    ) -> List[Tuple[str, pd.DataFrame]]:
        """
        거래대금 기준을 충족하는 미국 주식 목록과 데이터

        Returns:
            List of (ticker, DataFrame)
        """
        if min_trading_value is None:
            min_trading_value = self.US_MIN_TRADING_VALUE

        stock_list = self.get_us_stock_list()
        filtered_stocks = []

        logger.info(f"미국 주식 필터링 시작: {len(stock_list)}개 대상")

        def fetch_and_filter(stock_info):
            ticker = stock_info["ticker"]
            df = self.get_us_ohlcv(ticker)
            if df is not None and self.filter_by_trading_value(df, min_trading_value):
                return (ticker, df)
            return None

        with ThreadPoolExecutor(max_workers=max_workers) as executor:
            futures = {executor.submit(fetch_and_filter, s): s for s in stock_list}

            for future in as_completed(futures):
                result = future.result()
                if result:
                    filtered_stocks.append(result)

        logger.info(f"미국 주식 필터링 완료: {len(filtered_stocks)}개 통과")
        return filtered_stocks

    def get_filtered_kr_stocks(
        self,
        min_trading_value: float = None,
        market: str = "ALL",
        max_workers: int = 10
    ) -> List[Tuple[str, str, pd.DataFrame]]:
        """
        거래대금 기준을 충족하는 한국 주식 목록과 데이터

        Returns:
            List of (ticker, name, DataFrame)
        """
        if min_trading_value is None:
            min_trading_value = self.KR_MIN_TRADING_VALUE

        stock_list = self.get_kr_stock_list(market)
        filtered_stocks = []

        logger.info(f"한국 주식 필터링 시작: {len(stock_list)}개 대상")

        def fetch_and_filter(stock_info):
            ticker = stock_info["ticker"]
            name = stock_info.get("name", "")
            df = self.get_kr_ohlcv(ticker)
            if df is not None and self.filter_by_trading_value(df, min_trading_value):
                return (ticker, name, df)
            return None

        with ThreadPoolExecutor(max_workers=max_workers) as executor:
            futures = {executor.submit(fetch_and_filter, s): s for s in stock_list}

            for future in as_completed(futures):
                result = future.result()
                if result:
                    filtered_stocks.append(result)

        logger.info(f"한국 주식 필터링 완료: {len(filtered_stocks)}개 통과")
        return filtered_stocks


def get_stock_data_service() -> StockDataService:
    """StockDataService 인스턴스 생성"""
    return StockDataService()
