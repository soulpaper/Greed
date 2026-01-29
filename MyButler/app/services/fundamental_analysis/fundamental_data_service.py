# -*- coding: utf-8 -*-
"""
Fundamental Data Service
재무 데이터 수집 서비스 (yfinance for US, KIS API for KR)
"""
import logging
from datetime import datetime
from typing import Optional, Dict, Any, List
from concurrent.futures import ThreadPoolExecutor, as_completed

from app.models.fundamental_models import FundamentalData

logger = logging.getLogger(__name__)


class FundamentalDataService:
    """
    재무 데이터 수집 서비스

    데이터 소스:
    - 미국 주식: yfinance
    - 한국 주식: KIS API (finance_financial_ratio, finance_profit_ratio 등)
    """

    def __init__(self, use_kis: bool = True):
        """
        초기화

        Args:
            use_kis: KIS API 사용 여부 (한국 주식)
        """
        self.use_kis = use_kis

        # Lazy load
        self._yf = None
        self._kis_service = None

    @property
    def yf(self):
        """yfinance lazy import"""
        if self._yf is None:
            import yfinance as yf
            self._yf = yf
        return self._yf

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

    def get_us_fundamental_data(
        self,
        ticker: str,
        name: str = "",
        years: int = 10
    ) -> FundamentalData:
        """
        미국 주식 재무 데이터 수집 (yfinance 사용)

        Args:
            ticker: 종목 코드
            name: 종목명
            years: 조회할 연도 수

        Returns:
            FundamentalData 객체
        """
        data = FundamentalData(ticker=ticker, name=name, market="US")

        try:
            stock = self.yf.Ticker(ticker)

            # 재무제표 데이터 가져오기
            financials = stock.financials  # 손익계산서 (연간)
            balance_sheet = stock.balance_sheet  # 대차대조표 (연간)
            cash_flow = stock.cashflow  # 현금흐름표 (연간)

            # 현재 가격
            info = stock.info
            data.current_price = info.get("currentPrice", 0) or info.get("regularMarketPrice", 0) or 0

            if name == "":
                data.name = info.get("shortName", ticker)

            # 연도별 데이터 추출
            self._extract_us_roe_data(data, financials, balance_sheet)
            self._extract_us_gpm_data(data, financials)
            self._extract_us_debt_data(data, balance_sheet, financials)
            self._extract_us_capex_data(data, cash_flow, financials)

            data.is_valid = True

        except Exception as e:
            logger.warning(f"US 재무 데이터 수집 실패 {ticker}: {e}")
            data.is_valid = False
            data.error_message = str(e)

        return data

    def _extract_us_roe_data(
        self,
        data: FundamentalData,
        financials,
        balance_sheet
    ):
        """미국 주식 ROE 데이터 추출"""
        try:
            if financials is None or balance_sheet is None:
                return

            # Net Income 추출
            net_income_row = None
            for row_name in ["Net Income", "Net Income Common Stockholders"]:
                if row_name in financials.index:
                    net_income_row = financials.loc[row_name]
                    break

            # Total Stockholder Equity 추출
            equity_row = None
            for row_name in ["Total Stockholder Equity", "Stockholders Equity", "Total Equity Gross Minority Interest"]:
                if row_name in balance_sheet.index:
                    equity_row = balance_sheet.loc[row_name]
                    break

            if net_income_row is None or equity_row is None:
                return

            # 연도별 ROE 계산
            for col in net_income_row.index:
                try:
                    year = col.year if hasattr(col, 'year') else int(str(col)[:4])
                    net_income = float(net_income_row[col])

                    if col in equity_row.index:
                        equity = float(equity_row[col])
                        if equity > 0:
                            roe = (net_income / equity) * 100
                            data.roe_data[year] = round(roe, 2)
                except Exception:
                    continue

        except Exception as e:
            logger.debug(f"ROE 데이터 추출 실패: {e}")

    def _extract_us_gpm_data(
        self,
        data: FundamentalData,
        financials
    ):
        """미국 주식 GPM 데이터 추출"""
        try:
            if financials is None:
                return

            # Gross Profit & Revenue 추출
            gross_profit_row = None
            revenue_row = None

            for row_name in ["Gross Profit"]:
                if row_name in financials.index:
                    gross_profit_row = financials.loc[row_name]
                    break

            for row_name in ["Total Revenue", "Operating Revenue"]:
                if row_name in financials.index:
                    revenue_row = financials.loc[row_name]
                    break

            if gross_profit_row is None or revenue_row is None:
                return

            # 연도별 GPM 계산
            for col in gross_profit_row.index:
                try:
                    year = col.year if hasattr(col, 'year') else int(str(col)[:4])
                    gross_profit = float(gross_profit_row[col])

                    if col in revenue_row.index:
                        revenue = float(revenue_row[col])
                        if revenue > 0:
                            gpm = (gross_profit / revenue) * 100
                            data.gpm_data[year] = round(gpm, 2)
                except Exception:
                    continue

        except Exception as e:
            logger.debug(f"GPM 데이터 추출 실패: {e}")

    def _extract_us_debt_data(
        self,
        data: FundamentalData,
        balance_sheet,
        financials
    ):
        """미국 주식 부채 데이터 추출"""
        try:
            if balance_sheet is None or financials is None:
                return

            # 가장 최근 연도 데이터
            if len(balance_sheet.columns) == 0:
                return

            latest_col = balance_sheet.columns[0]

            # Total Debt 추출
            total_debt = 0
            for row_name in ["Total Debt", "Long Term Debt", "Long Term Debt And Capital Lease Obligation"]:
                if row_name in balance_sheet.index:
                    val = balance_sheet.loc[row_name, latest_col]
                    if not isinstance(val, (int, float)):
                        continue
                    total_debt = float(val)
                    break

            # Total Equity 추출
            total_equity = 0
            for row_name in ["Total Stockholder Equity", "Stockholders Equity", "Total Equity Gross Minority Interest"]:
                if row_name in balance_sheet.index:
                    val = balance_sheet.loc[row_name, latest_col]
                    if not isinstance(val, (int, float)):
                        continue
                    total_equity = float(val)
                    break

            # Net Income 추출
            net_income = 0
            if len(financials.columns) > 0:
                fin_latest_col = financials.columns[0]
                for row_name in ["Net Income", "Net Income Common Stockholders"]:
                    if row_name in financials.index:
                        val = financials.loc[row_name, fin_latest_col]
                        if not isinstance(val, (int, float)):
                            continue
                        net_income = float(val)
                        break

            data.total_debt = total_debt
            data.total_equity = total_equity
            data.net_income = net_income

        except Exception as e:
            logger.debug(f"부채 데이터 추출 실패: {e}")

    def _extract_us_capex_data(
        self,
        data: FundamentalData,
        cash_flow,
        financials
    ):
        """미국 주식 CapEx 데이터 추출"""
        try:
            if cash_flow is None or financials is None:
                return

            # Capital Expenditure 추출
            capex_row = None
            for row_name in ["Capital Expenditure", "Capital Expenditures"]:
                if row_name in cash_flow.index:
                    capex_row = cash_flow.loc[row_name]
                    break

            # Net Income 추출
            net_income_row = None
            for row_name in ["Net Income", "Net Income Common Stockholders"]:
                if row_name in financials.index:
                    net_income_row = financials.loc[row_name]
                    break

            if capex_row is None or net_income_row is None:
                return

            # 연도별 CapEx 및 Net Income
            for col in capex_row.index:
                try:
                    year = col.year if hasattr(col, 'year') else int(str(col)[:4])
                    capex = abs(float(capex_row[col]))  # CapEx는 음수로 표시되므로 절대값
                    data.capex_data[year] = capex

                    if col in net_income_row.index:
                        net_income = float(net_income_row[col])
                        data.net_income_data[year] = net_income
                except Exception:
                    continue

        except Exception as e:
            logger.debug(f"CapEx 데이터 추출 실패: {e}")

    def get_kr_fundamental_data(
        self,
        ticker: str,
        name: str = "",
        years: int = 10
    ) -> FundamentalData:
        """
        한국 주식 재무 데이터 수집 (KIS API 사용)

        Args:
            ticker: 종목 코드
            name: 종목명
            years: 조회할 연도 수

        Returns:
            FundamentalData 객체
        """
        data = FundamentalData(ticker=ticker, name=name, market="KR")

        if not self.use_kis or self.kis_service is None:
            data.is_valid = False
            data.error_message = "KIS 서비스 사용 불가"
            return data

        try:
            # KIS API를 통한 재무비율 조회
            financial_data = self._get_kr_financial_ratios(ticker)

            if financial_data:
                # ROE 데이터
                if "roe" in financial_data:
                    data.roe_data = financial_data["roe"]

                # GPM 데이터
                if "gpm" in financial_data:
                    data.gpm_data = financial_data["gpm"]

                # 부채 데이터
                if "debt_ratio" in financial_data:
                    data.total_debt = financial_data.get("total_debt", 0)
                    data.total_equity = financial_data.get("total_equity", 0)
                    data.net_income = financial_data.get("net_income", 0)

                # CapEx 데이터
                if "capex" in financial_data:
                    data.capex_data = financial_data["capex"]
                    data.net_income_data = financial_data.get("net_income_history", {})

                # 현재 가격
                data.current_price = financial_data.get("current_price", 0)

                data.is_valid = True
            else:
                data.is_valid = False
                data.error_message = "재무 데이터 조회 실패"

        except Exception as e:
            logger.warning(f"KR 재무 데이터 수집 실패 {ticker}: {e}")
            data.is_valid = False
            data.error_message = str(e)

        return data

    def _get_kr_financial_ratios(self, ticker: str) -> Optional[Dict[str, Any]]:
        """
        KIS API를 통한 한국 주식 재무비율 조회

        Returns:
            재무비율 딕셔너리 또는 None
        """
        try:
            if self.kis_service is None:
                return None

            # KIS API 호출 (finance_financial_ratio 등)
            # 참고: KIS API 메서드명은 실제 구현에 따라 다를 수 있음
            result = {}

            # 재무비율 조회 시도
            try:
                ratios = self.kis_service.get_financial_ratios(ticker)
                if ratios:
                    result.update(ratios)
            except AttributeError:
                logger.debug("KIS 서비스에 get_financial_ratios 메서드 없음")

            # 수익성 비율 조회 시도
            try:
                profit_ratios = self.kis_service.get_profit_ratios(ticker)
                if profit_ratios:
                    result.update(profit_ratios)
            except AttributeError:
                logger.debug("KIS 서비스에 get_profit_ratios 메서드 없음")

            # 현재가 조회
            try:
                price_info = self.kis_service.get_kr_current_price(ticker)
                if price_info:
                    result["current_price"] = price_info.get("price", 0)
            except Exception:
                pass

            return result if result else None

        except Exception as e:
            logger.debug(f"KIS 재무비율 조회 실패 {ticker}: {e}")
            return None

    def get_fundamental_data(
        self,
        ticker: str,
        name: str = "",
        market: str = "US",
        years: int = 10
    ) -> FundamentalData:
        """
        시장에 따른 재무 데이터 수집

        Args:
            ticker: 종목 코드
            name: 종목명
            market: 시장 (US, KR)
            years: 조회할 연도 수

        Returns:
            FundamentalData 객체
        """
        if market == "KR":
            return self.get_kr_fundamental_data(ticker, name, years)
        else:
            return self.get_us_fundamental_data(ticker, name, years)

    def get_fundamental_data_batch(
        self,
        stocks: List[Dict[str, str]],
        years: int = 10,
        max_workers: int = 5
    ) -> List[FundamentalData]:
        """
        여러 종목 재무 데이터 배치 수집

        Args:
            stocks: [{"ticker": str, "name": str, "market": str}, ...]
            years: 조회할 연도 수
            max_workers: 병렬 처리 워커 수

        Returns:
            FundamentalData 리스트
        """
        results = []

        def fetch_single(stock_info):
            ticker = stock_info["ticker"]
            name = stock_info.get("name", "")
            market = stock_info.get("market", "US")
            return self.get_fundamental_data(ticker, name, market, years)

        with ThreadPoolExecutor(max_workers=max_workers) as executor:
            futures = {executor.submit(fetch_single, s): s for s in stocks}

            for future in as_completed(futures):
                try:
                    result = future.result()
                    if result:
                        results.append(result)
                except Exception as e:
                    logger.debug(f"배치 데이터 수집 오류: {e}")

        return results


def get_fundamental_data_service() -> FundamentalDataService:
    """FundamentalDataService 인스턴스 생성"""
    return FundamentalDataService()
