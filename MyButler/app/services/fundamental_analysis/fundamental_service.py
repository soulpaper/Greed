# -*- coding: utf-8 -*-
"""
Fundamental Service
통합 펀더멘탈 분석 서비스
"""
import logging
from typing import List, Dict, Any, Optional, Tuple
from concurrent.futures import ThreadPoolExecutor, as_completed

from app.services.fundamental_analysis.fundamental_data_service import (
    FundamentalDataService,
    get_fundamental_data_service
)
from app.services.fundamental_analysis.roe_analyzer import ROEAnalyzer
from app.services.fundamental_analysis.gpm_analyzer import GPMAnalyzer
from app.services.fundamental_analysis.debt_analyzer import DebtAnalyzer
from app.services.fundamental_analysis.capex_analyzer import CapExAnalyzer
from app.models.fundamental_models import (
    FundamentalSignal,
    FundamentalData,
    ROESignal,
    GPMSignal,
    DebtSignal,
    CapExSignal,
)

logger = logging.getLogger(__name__)


class FundamentalService:
    """통합 펀더멘탈 분석 서비스"""

    # 보너스 점수 설정 (다중 조건 충족 시)
    BONUS_SCORES = {
        "roe": 5,
        "gpm": 5,
        "debt": 5,
        "capex": 5,
    }

    # 점수 임계값 (이 점수 이상이면 해당 조건 충족으로 판단)
    SCORE_THRESHOLDS = {
        "roe": 15,  # ROE 15점 이상 (최소 ROE 10% + 일관성 or 추세)
        "gpm": 15,  # GPM 15점 이상 (최소 GPM 30% + 3년 안정)
        "debt": 15,  # 부채 15점 이상 (최소 부채비율 50% or 상환능력)
        "capex": 10,  # CapEx 10점 이상 (최소 CapEx 25% 미만)
    }

    def __init__(self):
        self.data_service = get_fundamental_data_service()
        self.roe_analyzer = ROEAnalyzer()
        self.gpm_analyzer = GPMAnalyzer()
        self.debt_analyzer = DebtAnalyzer()
        self.capex_analyzer = CapExAnalyzer()

    def analyze_stock(
        self,
        data: FundamentalData,
        ticker: str,
        name: str = "",
        market: str = "US",
        filters: List[str] = None
    ) -> Optional[FundamentalSignal]:
        """
        종목 펀더멘탈 분석 수행

        Args:
            data: FundamentalData 객체
            ticker: 종목 코드
            name: 종목명
            market: 시장
            filters: 적용할 필터 목록 ["roe", "gpm", "debt", "capex"]

        Returns:
            FundamentalSignal or None
        """
        if data is None or not data.is_valid:
            return None

        if filters is None:
            filters = ["roe", "gpm", "debt", "capex"]

        current_price = data.current_price

        # 각 분석기 실행
        roe_signal = None
        gpm_signal = None
        debt_signal = None
        capex_signal = None

        if "roe" in filters:
            roe_signal = self.roe_analyzer.analyze(data, ticker, name, market)

        if "gpm" in filters:
            gpm_signal = self.gpm_analyzer.analyze(data, ticker, name, market)

        if "debt" in filters:
            debt_signal = self.debt_analyzer.analyze(data, ticker, name, market)

        if "capex" in filters:
            capex_signal = self.capex_analyzer.analyze(data, ticker, name, market)

        # 개별 점수 추출
        roe_score = roe_signal.score if roe_signal else 0
        gpm_score = gpm_signal.score if gpm_signal else 0
        debt_score = debt_signal.score if debt_signal else 0
        capex_score = capex_signal.score if capex_signal else 0

        # 활성 패턴 확인
        active_patterns = []
        if roe_score >= self.SCORE_THRESHOLDS["roe"]:
            active_patterns.append("roe_excellence")
        if gpm_score >= self.SCORE_THRESHOLDS["gpm"]:
            active_patterns.append("gpm_excellence")
        if debt_score >= self.SCORE_THRESHOLDS["debt"]:
            active_patterns.append("low_debt")
        if capex_score >= self.SCORE_THRESHOLDS["capex"]:
            active_patterns.append("capital_efficient")

        # 보너스 점수 계산 (2개 이상 충족 시)
        bonus_score = 0
        if len(active_patterns) >= 2:
            bonus_score = 5 * (len(active_patterns) - 1)

        # 통합 점수 (개별 점수 합 + 보너스)
        total_score = roe_score + gpm_score + debt_score + capex_score + bonus_score

        return FundamentalSignal(
            ticker=ticker,
            name=name or data.name,
            market=market,
            current_price=round(current_price, 2),
            roe=roe_signal,
            gpm=gpm_signal,
            debt=debt_signal,
            capex=capex_signal,
            total_score=total_score,
            active_patterns=active_patterns,
            roe_score=roe_score,
            gpm_score=gpm_score,
            debt_score=debt_score,
            capex_score=capex_score,
            bonus_score=bonus_score,
        )

    def analyze_stock_by_ticker(
        self,
        ticker: str,
        name: str = "",
        market: str = "US",
        filters: List[str] = None
    ) -> Optional[FundamentalSignal]:
        """
        종목 코드로 펀더멘탈 분석 수행

        Args:
            ticker: 종목 코드
            name: 종목명
            market: 시장
            filters: 적용할 필터 목록

        Returns:
            FundamentalSignal or None
        """
        # 재무 데이터 수집
        data = self.data_service.get_fundamental_data(ticker, name, market)

        if data is None or not data.is_valid:
            logger.debug(f"재무 데이터 없음: {ticker}")
            return None

        return self.analyze_stock(data, ticker, name, market, filters)

    def analyze_stocks_batch(
        self,
        stocks: List[Dict[str, str]],
        filters: List[str] = None,
        max_workers: int = 5
    ) -> List[FundamentalSignal]:
        """
        여러 종목 배치 분석

        Args:
            stocks: [{"ticker": str, "name": str, "market": str}, ...]
            filters: 적용할 필터 목록
            max_workers: 병렬 처리 워커 수

        Returns:
            FundamentalSignal 리스트
        """
        signals = []

        def analyze_single(stock_info):
            ticker = stock_info["ticker"]
            name = stock_info.get("name", "")
            market = stock_info.get("market", "US")
            return self.analyze_stock_by_ticker(ticker, name, market, filters)

        with ThreadPoolExecutor(max_workers=max_workers) as executor:
            futures = {executor.submit(analyze_single, s): s for s in stocks}

            for future in as_completed(futures):
                try:
                    result = future.result()
                    if result:
                        signals.append(result)
                except Exception as e:
                    logger.debug(f"배치 분석 오류: {e}")

        return signals

    def get_roe_excellence_signals(
        self,
        signals: List[FundamentalSignal],
        min_roe: float = 15.0,
        require_consistency: bool = False
    ) -> List[FundamentalSignal]:
        """
        ROE 우량 종목 필터링

        Args:
            signals: FundamentalSignal 리스트
            min_roe: 최소 ROE (%)
            require_consistency: 일관성 요구 여부

        Returns:
            필터링된 신호 리스트
        """
        filtered = []

        for signal in signals:
            if signal.roe is None:
                continue

            if signal.roe.current_roe < min_roe:
                continue

            if require_consistency and not (signal.roe.is_consistent or signal.roe.is_highly_consistent):
                continue

            filtered.append(signal)

        return sorted(filtered, key=lambda x: x.roe.current_roe, reverse=True)

    def filter_by_combine_mode(
        self,
        signals: List[FundamentalSignal],
        filters: List[str],
        combine_mode: str = "any",
        min_score: int = 10
    ) -> List[FundamentalSignal]:
        """
        조합 모드에 따른 필터링

        Args:
            signals: FundamentalSignal 리스트
            filters: 체크할 필터 목록
            combine_mode: "any" (OR) 또는 "all" (AND)
            min_score: 최소 점수

        Returns:
            필터링된 신호 리스트
        """
        filtered = []

        for signal in signals:
            passed_filters = []

            if "roe" in filters and signal.roe and signal.roe.score >= self.SCORE_THRESHOLDS["roe"]:
                passed_filters.append("roe")

            if "gpm" in filters and signal.gpm and signal.gpm.score >= self.SCORE_THRESHOLDS["gpm"]:
                passed_filters.append("gpm")

            if "debt" in filters and signal.debt and signal.debt.score >= self.SCORE_THRESHOLDS["debt"]:
                passed_filters.append("debt")

            if "capex" in filters and signal.capex and signal.capex.score >= self.SCORE_THRESHOLDS["capex"]:
                passed_filters.append("capex")

            if combine_mode == "all":
                # AND: 모든 필터 통과
                if len(passed_filters) == len(filters):
                    filtered.append(signal)
            else:
                # OR: 하나 이상 통과
                if len(passed_filters) > 0:
                    filtered.append(signal)

        return sorted(filtered, key=lambda x: x.total_score, reverse=True)

    def screen_by_roe(
        self,
        stocks: List[Dict[str, str]],
        min_roe: float = 15.0,
        require_consistency: bool = False,
        max_workers: int = 5
    ) -> List[FundamentalSignal]:
        """
        ROE 기준 스크리닝

        Args:
            stocks: 종목 목록
            min_roe: 최소 ROE
            require_consistency: 일관성 요구
            max_workers: 병렬 처리 워커 수

        Returns:
            ROE 우량 종목 리스트
        """
        signals = self.analyze_stocks_batch(stocks, filters=["roe"], max_workers=max_workers)
        return self.get_roe_excellence_signals(signals, min_roe, require_consistency)


def get_fundamental_service() -> FundamentalService:
    """FundamentalService 인스턴스 생성"""
    return FundamentalService()
