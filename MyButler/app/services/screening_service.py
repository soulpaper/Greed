# -*- coding: utf-8 -*-
"""
Screening Service
주식 스크리닝 서비스 (일목균형표 + 기술적 분석 + 펀더멘탈 분석 필터 통합)
"""
import logging
from datetime import date, datetime
from typing import List, Dict, Any, Optional, Tuple
from concurrent.futures import ThreadPoolExecutor, as_completed

import pandas as pd

from app.services.stock_data_service import get_stock_data_service, StockDataService
from app.services.ichimoku_service import get_ichimoku_service, IchimokuService, IchimokuSignal, SignalStrength
from app.services.technical_analysis.technical_service import get_technical_service, TechnicalService
from app.services.fundamental_analysis.fundamental_service import get_fundamental_service, FundamentalService
from app.models.screening_models import (
    StockSignal,
    ScreeningResponse,
    ScreeningResultCreate,
    MarketType,
    CombineMode,
)
from app.models.technical_models import TechnicalSignal
from app.models.fundamental_models import FundamentalSignal
from app.config.database_config import get_sqlite_connection
from app.utils.timezone_utils import format_date_for_db, parse_date_from_db

logger = logging.getLogger(__name__)


class ScreeningService:
    """주식 스크리닝 서비스"""

    # 기술적 분석 보너스 점수
    TECHNICAL_BONUS = {
        "bollinger": 15,
        "ma_alignment": 15,
        "cup_handle": 20,
    }

    # 기술적 분석 점수 임계값
    TECHNICAL_THRESHOLD = 40

    # 펀더멘탈 분석 점수 임계값
    FUNDAMENTAL_THRESHOLD = {
        "roe": 15,
        "gpm": 15,
        "debt": 15,
        "capex": 10,
    }

    # 펀더멘탈 필터 목록
    FUNDAMENTAL_FILTERS = ["roe", "gpm", "debt", "capex"]

    def __init__(self):
        self.stock_data_service = get_stock_data_service()
        self.ichimoku_service = get_ichimoku_service()
        self.technical_service = get_technical_service()
        self.fundamental_service = get_fundamental_service()

    def _signal_to_stock_signal(
        self,
        signal: IchimokuSignal,
        technical_signal: Optional[TechnicalSignal] = None
    ) -> StockSignal:
        """IchimokuSignal + TechnicalSignal을 StockSignal로 변환"""
        # 기본 일목균형표 정보
        stock_signal = StockSignal(
            ticker=signal.ticker,
            name=signal.name,
            market=signal.market,
            current_price=signal.current_price,
            signal_strength=signal.signal_strength.value,
            score=signal.score,
            price_above_cloud=signal.price_above_cloud,
            tenkan_above_kijun=signal.tenkan_above_kijun,
            chikou_above_price=signal.chikou_above_price,
            cloud_bullish=signal.cloud_bullish,
            cloud_breakout=signal.cloud_breakout,
            golden_cross=signal.golden_cross,
            thin_cloud=signal.thin_cloud,
            tenkan_sen=signal.tenkan_sen,
            kijun_sen=signal.kijun_sen,
            senkou_span_a=signal.senkou_span_a,
            senkou_span_b=signal.senkou_span_b,
            ichimoku_disparity=signal.disparity,
            ichimoku_disparity_score=signal.disparity_score,
            ichimoku_disparity_optimal=signal.disparity_optimal,
            ichimoku_disparity_overheated=signal.disparity_overheated,
            avg_trading_value=signal.avg_trading_value,
        )

        # 기술적 분석 정보 추가
        if technical_signal:
            # 볼린저 밴드
            if technical_signal.bollinger:
                bb = technical_signal.bollinger
                stock_signal.bollinger_squeeze = bb.is_squeeze or bb.is_strong_squeeze
                stock_signal.bollinger_score = bb.score
                stock_signal.bollinger_bandwidth = bb.bandwidth
                stock_signal.bollinger_percent_b = bb.percent_b

            # 이동평균 정배열
            if technical_signal.ma_alignment:
                ma = technical_signal.ma_alignment
                stock_signal.ma_perfect_alignment = ma.is_perfect_alignment
                stock_signal.ma_alignment_score = ma.score
                stock_signal.ma_disparity = ma.disparity

            # 컵앤핸들
            if technical_signal.cup_handle:
                ch = technical_signal.cup_handle
                stock_signal.cup_handle_pattern = ch.cup_detected
                stock_signal.cup_handle_score = ch.score
                stock_signal.cup_handle_breakout_imminent = ch.breakout_imminent

            # 보너스 및 통합 점수
            stock_signal.bonus_score = technical_signal.bonus_score
            stock_signal.total_technical_score = technical_signal.total_score
            stock_signal.active_patterns = technical_signal.active_patterns

        return stock_signal

    def _create_stock_signal_from_technical(
        self,
        technical_signal: TechnicalSignal
    ) -> StockSignal:
        """TechnicalSignal만으로 StockSignal 생성 (일목균형표 없이)"""
        return StockSignal(
            ticker=technical_signal.ticker,
            name=technical_signal.name,
            market=technical_signal.market,
            current_price=technical_signal.current_price,
            signal_strength="TECHNICAL",
            score=technical_signal.total_score,
            # 볼린저 밴드
            bollinger_squeeze=(
                technical_signal.bollinger.is_squeeze
                if technical_signal.bollinger else False
            ),
            bollinger_score=technical_signal.bollinger_score,
            bollinger_bandwidth=(
                technical_signal.bollinger.bandwidth
                if technical_signal.bollinger else None
            ),
            bollinger_percent_b=(
                technical_signal.bollinger.percent_b
                if technical_signal.bollinger else None
            ),
            # 이동평균 정배열
            ma_perfect_alignment=(
                technical_signal.ma_alignment.is_perfect_alignment
                if technical_signal.ma_alignment else False
            ),
            ma_alignment_score=technical_signal.ma_alignment_score,
            ma_disparity=(
                technical_signal.ma_alignment.disparity
                if technical_signal.ma_alignment else None
            ),
            # 컵앤핸들
            cup_handle_pattern=(
                technical_signal.cup_handle.cup_detected
                if technical_signal.cup_handle else False
            ),
            cup_handle_score=technical_signal.cup_handle_score,
            cup_handle_breakout_imminent=(
                technical_signal.cup_handle.breakout_imminent
                if technical_signal.cup_handle else False
            ),
            # 통합 점수
            bonus_score=technical_signal.bonus_score,
            total_technical_score=technical_signal.total_score,
            active_patterns=technical_signal.active_patterns,
        )

    def _merge_fundamental_signal(
        self,
        stock_signal: StockSignal,
        fundamental_signal: Optional[FundamentalSignal]
    ) -> StockSignal:
        """펀더멘탈 신호를 StockSignal에 병합"""
        if fundamental_signal is None:
            return stock_signal

        # ROE 정보
        if fundamental_signal.roe:
            stock_signal.roe_score = fundamental_signal.roe.score
            stock_signal.roe_value = fundamental_signal.roe.current_roe
            stock_signal.roe_consistent = (
                fundamental_signal.roe.is_consistent or
                fundamental_signal.roe.is_highly_consistent
            )

        # GPM 정보
        if fundamental_signal.gpm:
            stock_signal.gpm_score = fundamental_signal.gpm.score
            stock_signal.gpm_value = fundamental_signal.gpm.current_gpm

        # Debt 정보
        if fundamental_signal.debt:
            stock_signal.debt_score = fundamental_signal.debt.score
            stock_signal.debt_ratio = fundamental_signal.debt.current_debt_ratio

        # CapEx 정보
        if fundamental_signal.capex:
            stock_signal.capex_score = fundamental_signal.capex.score
            stock_signal.capex_ratio = fundamental_signal.capex.capex_to_income_ratio

        # 통합 펀더멘탈 점수
        stock_signal.total_fundamental_score = fundamental_signal.total_score
        stock_signal.fundamental_patterns = fundamental_signal.active_patterns

        return stock_signal

    def _create_stock_signal_from_fundamental(
        self,
        fundamental_signal: FundamentalSignal
    ) -> StockSignal:
        """FundamentalSignal만으로 StockSignal 생성"""
        stock_signal = StockSignal(
            ticker=fundamental_signal.ticker,
            name=fundamental_signal.name,
            market=fundamental_signal.market,
            current_price=fundamental_signal.current_price,
            signal_strength="FUNDAMENTAL",
            score=fundamental_signal.total_score,
        )

        # ROE 정보
        if fundamental_signal.roe:
            stock_signal.roe_score = fundamental_signal.roe.score
            stock_signal.roe_value = fundamental_signal.roe.current_roe
            stock_signal.roe_consistent = (
                fundamental_signal.roe.is_consistent or
                fundamental_signal.roe.is_highly_consistent
            )

        # GPM 정보
        if fundamental_signal.gpm:
            stock_signal.gpm_score = fundamental_signal.gpm.score
            stock_signal.gpm_value = fundamental_signal.gpm.current_gpm

        # Debt 정보
        if fundamental_signal.debt:
            stock_signal.debt_score = fundamental_signal.debt.score
            stock_signal.debt_ratio = fundamental_signal.debt.current_debt_ratio

        # CapEx 정보
        if fundamental_signal.capex:
            stock_signal.capex_score = fundamental_signal.capex.score
            stock_signal.capex_ratio = fundamental_signal.capex.capex_to_income_ratio

        # 통합 펀더멘탈 점수
        stock_signal.total_fundamental_score = fundamental_signal.total_score
        stock_signal.fundamental_patterns = fundamental_signal.active_patterns

        return stock_signal

    def screen_us_stocks(
        self,
        min_score: int = 50,
        perfect_only: bool = False,
        max_workers: int = 10,
        filters: List[str] = None,
        combine_mode: str = "any"
    ) -> Tuple[List[StockSignal], int, int]:
        """
        미국 주식 스크리닝

        Returns:
            (signals, total_scanned, total_passed_filter)
        """
        logger.info("미국 주식 스크리닝 시작")

        if filters is None:
            filters = ["ichimoku"]

        # 거래대금 필터링된 주식 가져오기
        filtered_stocks = self.stock_data_service.get_filtered_us_stocks(max_workers=max_workers)
        total_scanned = len(self.stock_data_service.get_us_stock_list())
        total_passed_filter = len(filtered_stocks)

        logger.info(f"거래대금 필터 통과: {total_passed_filter}/{total_scanned}")

        # DataFrame 딕셔너리 생성
        stock_data = {ticker: df for ticker, df in filtered_stocks}

        # 분석 수행
        signals = self._analyze_stocks(
            stock_data=stock_data,
            market="US",
            filters=filters,
            combine_mode=combine_mode,
            min_score=min_score,
            perfect_only=perfect_only,
        )

        logger.info(f"최종 신호: {len(signals)}개")

        return signals, total_scanned, total_passed_filter

    def screen_kr_stocks(
        self,
        min_score: int = 50,
        perfect_only: bool = False,
        market: str = "ALL",
        max_workers: int = 10,
        filters: List[str] = None,
        combine_mode: str = "any"
    ) -> Tuple[List[StockSignal], int, int]:
        """
        한국 주식 스크리닝

        Returns:
            (signals, total_scanned, total_passed_filter)
        """
        logger.info("한국 주식 스크리닝 시작")

        if filters is None:
            filters = ["ichimoku"]

        # 거래대금 필터링된 주식 가져오기
        filtered_stocks = self.stock_data_service.get_filtered_kr_stocks(market=market, max_workers=max_workers)
        total_scanned = len(self.stock_data_service.get_kr_stock_list(market))
        total_passed_filter = len(filtered_stocks)

        logger.info(f"거래대금 필터 통과: {total_passed_filter}/{total_scanned}")

        # DataFrame 딕셔너리 생성 (이름 포함)
        stock_data = {}
        stock_names = {}
        for ticker, name, df in filtered_stocks:
            stock_data[ticker] = df
            stock_names[ticker] = name

        # 분석 수행
        signals = self._analyze_stocks(
            stock_data=stock_data,
            market="KR",
            filters=filters,
            combine_mode=combine_mode,
            min_score=min_score,
            perfect_only=perfect_only,
            stock_names=stock_names,
        )

        logger.info(f"최종 신호: {len(signals)}개")

        return signals, total_scanned, total_passed_filter

    def _analyze_stocks(
        self,
        stock_data: Dict[str, pd.DataFrame],
        market: str,
        filters: List[str],
        combine_mode: str,
        min_score: int,
        perfect_only: bool,
        stock_names: Dict[str, str] = None
    ) -> List[StockSignal]:
        """주식 분석 수행"""
        if stock_names is None:
            stock_names = {}

        signals = []
        use_ichimoku = "ichimoku" in filters
        technical_filters = [f for f in filters if f != "ichimoku" and f not in self.FUNDAMENTAL_FILTERS]
        fundamental_filters = [f for f in filters if f in self.FUNDAMENTAL_FILTERS]

        for ticker, df in stock_data.items():
            name = stock_names.get(ticker, ticker)

            # 일목균형표 분석
            ichimoku_signal = None
            if use_ichimoku:
                ichimoku_signal = self.ichimoku_service.analyze_signal(df, ticker, name, market)

            # 기술적 분석
            technical_signal = None
            if technical_filters:
                technical_signal = self.technical_service.analyze_stock(
                    df, ticker, name, market, technical_filters
                )

            # 펀더멘탈 분석
            fundamental_signal = None
            if fundamental_filters:
                fundamental_signal = self.fundamental_service.analyze_stock_by_ticker(
                    ticker, name, market, fundamental_filters
                )

            # 조합 모드에 따른 필터링
            if combine_mode == "all":
                # AND 모드: 모든 필터 통과 필요
                if not self._passes_all_filters(
                    ichimoku_signal, technical_signal, fundamental_signal, filters, min_score, perfect_only
                ):
                    continue
            else:
                # OR 모드: 하나 이상 통과
                if not self._passes_any_filter(
                    ichimoku_signal, technical_signal, fundamental_signal, filters, min_score, perfect_only
                ):
                    continue

            # StockSignal 생성
            if ichimoku_signal:
                stock_signal = self._signal_to_stock_signal(ichimoku_signal, technical_signal)
            elif technical_signal:
                stock_signal = self._create_stock_signal_from_technical(technical_signal)
            elif fundamental_signal:
                stock_signal = self._create_stock_signal_from_fundamental(fundamental_signal)
            else:
                continue

            # 펀더멘탈 신호 병합
            if fundamental_signal and (ichimoku_signal or technical_signal):
                stock_signal = self._merge_fundamental_signal(stock_signal, fundamental_signal)

            # 보너스 점수 계산 및 적용
            if technical_signal and ichimoku_signal:
                bonus = self._calculate_cross_filter_bonus(technical_signal)
                stock_signal.score += bonus
                stock_signal.bonus_score = bonus

            signals.append(stock_signal)

        # 점수순 정렬
        return sorted(signals, key=lambda x: x.score, reverse=True)

    def _passes_all_filters(
        self,
        ichimoku: Optional[IchimokuSignal],
        technical: Optional[TechnicalSignal],
        fundamental: Optional[FundamentalSignal],
        filters: List[str],
        min_score: int,
        perfect_only: bool
    ) -> bool:
        """모든 필터 통과 여부 (AND 모드)"""
        for f in filters:
            if f == "ichimoku":
                if not ichimoku:
                    return False
                if perfect_only:
                    if not (ichimoku.price_above_cloud and
                            ichimoku.tenkan_above_kijun and
                            ichimoku.chikou_above_price):
                        return False
                elif ichimoku.score < min_score:
                    return False

            elif f == "bollinger":
                if not technical or not technical.bollinger:
                    return False
                if technical.bollinger.score < self.TECHNICAL_THRESHOLD:
                    return False

            elif f == "ma_alignment":
                if not technical or not technical.ma_alignment:
                    return False
                if technical.ma_alignment.score < self.TECHNICAL_THRESHOLD:
                    return False

            elif f == "cup_handle":
                if not technical or not technical.cup_handle:
                    return False
                if not technical.cup_handle.cup_detected:
                    return False
                if technical.cup_handle.score < self.TECHNICAL_THRESHOLD:
                    return False

            # 펀더멘탈 필터
            elif f == "roe":
                if not fundamental or not fundamental.roe:
                    return False
                if fundamental.roe.score < self.FUNDAMENTAL_THRESHOLD["roe"]:
                    return False

            elif f == "gpm":
                if not fundamental or not fundamental.gpm:
                    return False
                if fundamental.gpm.score < self.FUNDAMENTAL_THRESHOLD["gpm"]:
                    return False

            elif f == "debt":
                if not fundamental or not fundamental.debt:
                    return False
                if fundamental.debt.score < self.FUNDAMENTAL_THRESHOLD["debt"]:
                    return False

            elif f == "capex":
                if not fundamental or not fundamental.capex:
                    return False
                if fundamental.capex.score < self.FUNDAMENTAL_THRESHOLD["capex"]:
                    return False

        return True

    def _passes_any_filter(
        self,
        ichimoku: Optional[IchimokuSignal],
        technical: Optional[TechnicalSignal],
        fundamental: Optional[FundamentalSignal],
        filters: List[str],
        min_score: int,
        perfect_only: bool
    ) -> bool:
        """하나 이상 필터 통과 여부 (OR 모드)"""
        for f in filters:
            if f == "ichimoku":
                if ichimoku:
                    if perfect_only:
                        if (ichimoku.price_above_cloud and
                            ichimoku.tenkan_above_kijun and
                            ichimoku.chikou_above_price):
                            return True
                    elif ichimoku.score >= min_score:
                        return True

            elif f == "bollinger":
                if technical and technical.bollinger:
                    if technical.bollinger.score >= self.TECHNICAL_THRESHOLD:
                        return True

            elif f == "ma_alignment":
                if technical and technical.ma_alignment:
                    if technical.ma_alignment.score >= self.TECHNICAL_THRESHOLD:
                        return True

            elif f == "cup_handle":
                if technical and technical.cup_handle:
                    if (technical.cup_handle.cup_detected and
                        technical.cup_handle.score >= self.TECHNICAL_THRESHOLD):
                        return True

            # 펀더멘탈 필터
            elif f == "roe":
                if fundamental and fundamental.roe:
                    if fundamental.roe.score >= self.FUNDAMENTAL_THRESHOLD["roe"]:
                        return True

            elif f == "gpm":
                if fundamental and fundamental.gpm:
                    if fundamental.gpm.score >= self.FUNDAMENTAL_THRESHOLD["gpm"]:
                        return True

            elif f == "debt":
                if fundamental and fundamental.debt:
                    if fundamental.debt.score >= self.FUNDAMENTAL_THRESHOLD["debt"]:
                        return True

            elif f == "capex":
                if fundamental and fundamental.capex:
                    if fundamental.capex.score >= self.FUNDAMENTAL_THRESHOLD["capex"]:
                        return True

        return False

    def _calculate_cross_filter_bonus(self, technical: TechnicalSignal) -> int:
        """다중 필터 충족 보너스 계산"""
        bonus = 0
        active_count = len(technical.active_patterns)

        if active_count >= 2:
            # 2개 이상 패턴 충족 시 추가 보너스
            bonus += 10 * (active_count - 1)

        return bonus

    def run_screening(
        self,
        market: MarketType = MarketType.ALL,
        min_score: int = 50,
        perfect_only: bool = False,
        limit: int = 20,
        filters: List[str] = None,
        combine_mode: str = "any"
    ) -> ScreeningResponse:
        """
        전체 스크리닝 실행

        Args:
            market: 대상 시장 (US, KR, ALL)
            min_score: 최소 점수
            perfect_only: 완벽 조건만
            limit: 결과 개수
            filters: 적용할 필터 목록
            combine_mode: 필터 조합 모드 (any/all)

        Returns:
            ScreeningResponse
        """
        if filters is None:
            filters = ["ichimoku"]

        screening_date = date.today()
        all_signals: List[StockSignal] = []
        total_scanned = 0
        total_passed_filter = 0

        # 미국 주식 스크리닝
        if market in [MarketType.US, MarketType.ALL]:
            us_signals, us_scanned, us_passed = self.screen_us_stocks(
                min_score, perfect_only, filters=filters, combine_mode=combine_mode
            )
            all_signals.extend(us_signals)
            total_scanned += us_scanned
            total_passed_filter += us_passed

        # 한국 주식 스크리닝
        if market in [MarketType.KR, MarketType.ALL]:
            kr_signals, kr_scanned, kr_passed = self.screen_kr_stocks(
                min_score, perfect_only, filters=filters, combine_mode=combine_mode
            )
            all_signals.extend(kr_signals)
            total_scanned += kr_scanned
            total_passed_filter += kr_passed

        # 점수순 정렬
        all_signals = sorted(all_signals, key=lambda x: x.score, reverse=True)

        # 신호 강도별 분류
        strong_buy = []
        buy = []
        weak_buy = []

        for signal in all_signals[:limit * 3]:  # 여유있게 가져옴
            if signal.score >= 80:
                if len(strong_buy) < limit:
                    strong_buy.append(signal)
            elif signal.score >= 50:
                if len(buy) < limit:
                    buy.append(signal)
            elif signal.score >= 20:
                if len(weak_buy) < limit:
                    weak_buy.append(signal)

        # 요약
        summary = {
            "total_strong_buy": len(strong_buy),
            "total_buy": len(buy),
            "total_weak_buy": len(weak_buy),
            "avg_score": round(sum(s.score for s in all_signals) / len(all_signals), 1) if all_signals else 0,
            "filters_used": filters,
            "combine_mode": combine_mode,
            # 기술적 분석 패턴별 통계
            "bollinger_squeeze_count": len([s for s in all_signals if s.bollinger_squeeze]),
            "ma_alignment_count": len([s for s in all_signals if s.ma_perfect_alignment]),
            "cup_handle_count": len([s for s in all_signals if s.cup_handle_pattern]),
        }

        # 일목균형표 관련 통계 (ichimoku 필터 사용 시)
        if "ichimoku" in filters:
            summary["perfect_signals"] = len([
                s for s in all_signals
                if s.price_above_cloud and s.tenkan_above_kijun and s.chikou_above_price
            ])
            summary["cloud_breakouts"] = len([s for s in all_signals if s.cloud_breakout])
            summary["golden_crosses"] = len([s for s in all_signals if s.golden_cross])

        # 펀더멘탈 관련 통계 (펀더멘탈 필터 사용 시)
        has_fundamental = any(f in self.FUNDAMENTAL_FILTERS for f in filters)
        if has_fundamental:
            summary["roe_excellence_count"] = len([s for s in all_signals if s.roe_score >= 15])
            summary["gpm_excellence_count"] = len([s for s in all_signals if s.gpm_score >= 15])
            summary["low_debt_count"] = len([s for s in all_signals if s.debt_score >= 15])
            summary["capital_efficient_count"] = len([s for s in all_signals if s.capex_score >= 10])

        return ScreeningResponse(
            screening_date=screening_date,
            market=market.value,
            total_scanned=total_scanned,
            total_passed_filter=total_passed_filter,
            total_signals=len(all_signals),
            strong_buy=strong_buy,
            buy=buy,
            weak_buy=weak_buy,
            summary=summary,
        )

    def run_bollinger_screening(
        self,
        market: MarketType = MarketType.ALL,
        min_score: int = 40,
        limit: int = 20
    ) -> ScreeningResponse:
        """볼린저 스퀴즈 전용 스크리닝"""
        return self.run_screening(
            market=market,
            min_score=min_score,
            limit=limit,
            filters=["bollinger"],
            combine_mode="any"
        )

    def run_ma_alignment_screening(
        self,
        market: MarketType = MarketType.ALL,
        min_score: int = 40,
        limit: int = 20
    ) -> ScreeningResponse:
        """이평선 정배열 전용 스크리닝"""
        return self.run_screening(
            market=market,
            min_score=min_score,
            limit=limit,
            filters=["ma_alignment"],
            combine_mode="any"
        )

    def run_cup_handle_screening(
        self,
        market: MarketType = MarketType.ALL,
        min_score: int = 40,
        limit: int = 20
    ) -> ScreeningResponse:
        """컵앤핸들 전용 스크리닝"""
        return self.run_screening(
            market=market,
            min_score=min_score,
            limit=limit,
            filters=["cup_handle"],
            combine_mode="any"
        )

    def run_fundamental_screening(
        self,
        market: MarketType = MarketType.ALL,
        min_score: int = 40,
        limit: int = 20,
        filters: List[str] = None
    ) -> ScreeningResponse:
        """
        펀더멘탈 분석 전용 스크리닝

        Args:
            market: 대상 시장
            min_score: 최소 점수
            limit: 결과 개수
            filters: 펀더멘탈 필터 ["roe", "gpm", "debt", "capex"]
        """
        if filters is None:
            filters = ["roe", "gpm", "debt", "capex"]

        # 펀더멘탈 필터만 허용
        valid_filters = [f for f in filters if f in self.FUNDAMENTAL_FILTERS]
        if not valid_filters:
            valid_filters = self.FUNDAMENTAL_FILTERS

        return self.run_screening(
            market=market,
            min_score=min_score,
            limit=limit,
            filters=valid_filters,
            combine_mode="any"
        )

    def run_roe_excellence_screening(
        self,
        market: MarketType = MarketType.ALL,
        min_roe: float = 15.0,
        require_consistency: bool = False,
        limit: int = 20
    ) -> ScreeningResponse:
        """
        ROE 우량 종목 스크리닝

        Args:
            market: 대상 시장
            min_roe: 최소 ROE (%)
            require_consistency: 일관성 요구 여부
            limit: 결과 개수
        """
        # 기본 ROE 스크리닝 실행
        response = self.run_screening(
            market=market,
            min_score=0,  # 점수 무관, ROE 직접 체크
            limit=limit * 3,  # 여유있게 가져옴
            filters=["roe"],
            combine_mode="any"
        )

        # ROE 필터링
        filtered_signals = []
        for signal in response.strong_buy + response.buy + response.weak_buy:
            if signal.roe_value is None:
                continue
            if signal.roe_value < min_roe:
                continue
            if require_consistency and not signal.roe_consistent:
                continue
            filtered_signals.append(signal)

        # ROE 값으로 정렬
        filtered_signals = sorted(filtered_signals, key=lambda x: x.roe_value or 0, reverse=True)

        # 신호 강도별 재분류
        strong_buy = []
        buy = []
        weak_buy = []

        for signal in filtered_signals[:limit * 3]:
            if signal.roe_score >= 25:
                if len(strong_buy) < limit:
                    strong_buy.append(signal)
            elif signal.roe_score >= 15:
                if len(buy) < limit:
                    buy.append(signal)
            else:
                if len(weak_buy) < limit:
                    weak_buy.append(signal)

        response.strong_buy = strong_buy
        response.buy = buy
        response.weak_buy = weak_buy
        response.total_signals = len(filtered_signals)
        response.summary["min_roe_filter"] = min_roe
        response.summary["require_consistency"] = require_consistency

        return response

    async def save_screening_results(
        self,
        signals: List[StockSignal],
        screening_date: date = None
    ) -> int:
        """스크리닝 결과 DB 저장 (필터별 점수 포함)"""
        if screening_date is None:
            screening_date = date.today()

        conn = await get_sqlite_connection()
        try:
            cursor = await conn.cursor()
            saved_count = 0

            for signal in signals:
                await cursor.execute("""
                    INSERT INTO screening_results
                    (screening_date, ticker, name, market, current_price, signal_strength,
                     score, price_above_cloud, tenkan_above_kijun, chikou_above_price,
                     cloud_bullish, cloud_breakout, golden_cross, avg_trading_value,
                     ichimoku_disparity, ichimoku_disparity_score,
                     bollinger_score, ma_alignment_score, cup_handle_score, total_technical_score,
                     roe_score, gpm_score, debt_score, capex_score, total_fundamental_score)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    ON CONFLICT(screening_date, ticker) DO UPDATE SET
                        current_price = excluded.current_price,
                        signal_strength = excluded.signal_strength,
                        score = excluded.score,
                        price_above_cloud = excluded.price_above_cloud,
                        tenkan_above_kijun = excluded.tenkan_above_kijun,
                        chikou_above_price = excluded.chikou_above_price,
                        cloud_bullish = excluded.cloud_bullish,
                        cloud_breakout = excluded.cloud_breakout,
                        golden_cross = excluded.golden_cross,
                        avg_trading_value = excluded.avg_trading_value,
                        ichimoku_disparity = excluded.ichimoku_disparity,
                        ichimoku_disparity_score = excluded.ichimoku_disparity_score,
                        bollinger_score = excluded.bollinger_score,
                        ma_alignment_score = excluded.ma_alignment_score,
                        cup_handle_score = excluded.cup_handle_score,
                        total_technical_score = excluded.total_technical_score,
                        roe_score = excluded.roe_score,
                        gpm_score = excluded.gpm_score,
                        debt_score = excluded.debt_score,
                        capex_score = excluded.capex_score,
                        total_fundamental_score = excluded.total_fundamental_score
                """, (
                    format_date_for_db(screening_date),
                    signal.ticker,
                    signal.name,
                    signal.market,
                    signal.current_price,
                    signal.signal_strength,
                    signal.score,
                    signal.price_above_cloud,
                    signal.tenkan_above_kijun,
                    signal.chikou_above_price,
                    signal.cloud_bullish,
                    signal.cloud_breakout,
                    signal.golden_cross,
                    signal.avg_trading_value,
                    signal.ichimoku_disparity,
                    signal.ichimoku_disparity_score,
                    signal.bollinger_score,
                    signal.ma_alignment_score,
                    signal.cup_handle_score,
                    signal.total_technical_score,
                    signal.roe_score,
                    signal.gpm_score,
                    signal.debt_score,
                    signal.capex_score,
                    signal.total_fundamental_score,
                ))
                saved_count += 1

            await conn.commit()
            logger.info(f"스크리닝 결과 저장 완료: {saved_count}개 (필터별 점수 포함)")
            return saved_count

        finally:
            await conn.close()

    async def get_screening_history(
        self,
        start_date: Optional[date] = None,
        end_date: Optional[date] = None,
        market: Optional[str] = None,
        ticker: Optional[str] = None,
        min_score: int = 50,
        limit: int = 100,
        offset: int = 0
    ) -> Tuple[List[Dict], int]:
        """스크리닝 히스토리 조회"""
        conn = await get_sqlite_connection()
        try:
            cursor = await conn.cursor()

            where_clauses = ["score >= ?"]
            params = [min_score]

            if start_date:
                where_clauses.append("screening_date >= ?")
                params.append(format_date_for_db(start_date))
            if end_date:
                where_clauses.append("screening_date <= ?")
                params.append(format_date_for_db(end_date))
            if market:
                where_clauses.append("market = ?")
                params.append(market)
            if ticker:
                where_clauses.append("ticker = ?")
                params.append(ticker)

            where_sql = " AND ".join(where_clauses)

            # 총 개수
            await cursor.execute(f"SELECT COUNT(*) FROM screening_results WHERE {where_sql}", params)
            total_count = (await cursor.fetchone())[0]

            # 데이터 조회
            await cursor.execute(f"""
                SELECT * FROM screening_results
                WHERE {where_sql}
                ORDER BY screening_date DESC, score DESC
                LIMIT ? OFFSET ?
            """, params + [limit, offset])

            records = []
            async for row in cursor:
                records.append(dict(row))

            return records, total_count

        finally:
            await conn.close()

    async def get_latest_recommendations(
        self,
        market: Optional[str] = None,
        limit: int = 10
    ) -> Dict[str, Any]:
        """최신 추천 종목 조회"""
        conn = await get_sqlite_connection()
        try:
            cursor = await conn.cursor()

            # 가장 최근 스크리닝 날짜
            await cursor.execute("SELECT MAX(screening_date) FROM screening_results")
            row = await cursor.fetchone()
            if not row or not row[0]:
                return {"date": None, "recommendations": [], "total": 0}

            latest_date = row[0]

            # 해당 날짜의 추천 종목
            where_clause = "screening_date = ? AND score >= 50"
            params = [latest_date]

            if market:
                where_clause += " AND market = ?"
                params.append(market)

            await cursor.execute(f"""
                SELECT * FROM screening_results
                WHERE {where_clause}
                ORDER BY score DESC
                LIMIT ?
            """, params + [limit])

            recommendations = []
            async for row in cursor:
                recommendations.append(dict(row))

            return {
                "date": latest_date,
                "recommendations": recommendations,
                "total": len(recommendations)
            }

        finally:
            await conn.close()


def get_screening_service() -> ScreeningService:
    """ScreeningService 인스턴스 생성"""
    return ScreeningService()
