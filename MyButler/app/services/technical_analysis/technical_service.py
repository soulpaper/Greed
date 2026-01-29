# -*- coding: utf-8 -*-
"""
Technical Service
통합 기술적 분석 서비스
"""
import logging
from typing import List, Dict, Any, Optional, Tuple
from concurrent.futures import ThreadPoolExecutor, as_completed

import pandas as pd

from app.services.technical_analysis.bollinger_analyzer import BollingerAnalyzer
from app.services.technical_analysis.ma_alignment_analyzer import MAAlignmentAnalyzer
from app.services.technical_analysis.cup_handle_analyzer import CupHandleAnalyzer
from app.models.technical_models import (
    TechnicalSignal,
    BollingerSignal,
    MAAlignmentSignal,
    CupHandleSignal,
)

logger = logging.getLogger(__name__)


class TechnicalService:
    """통합 기술적 분석 서비스"""

    # 보너스 점수 설정
    BONUS_SCORES = {
        "bollinger": 15,  # 볼린저 스퀴즈 충족 시 보너스
        "ma_alignment": 15,  # 이평선 정배열 충족 시 보너스
        "cup_handle": 20,  # 컵앤핸들 패턴 충족 시 보너스
    }

    # 점수 임계값 (이 점수 이상이면 해당 패턴 충족으로 판단)
    SCORE_THRESHOLDS = {
        "bollinger": 40,  # 볼린저 40점 이상
        "ma_alignment": 40,  # 이평선 40점 이상
        "cup_handle": 40,  # 컵앤핸들 40점 이상
    }

    def __init__(self):
        self.bollinger_analyzer = BollingerAnalyzer()
        self.ma_alignment_analyzer = MAAlignmentAnalyzer()
        self.cup_handle_analyzer = CupHandleAnalyzer()

    def analyze_stock(
        self,
        df: pd.DataFrame,
        ticker: str,
        name: str = "",
        market: str = "US",
        filters: List[str] = None
    ) -> Optional[TechnicalSignal]:
        """
        종목 기술적 분석 수행

        Args:
            df: OHLCV DataFrame
            ticker: 종목 코드
            name: 종목명
            market: 시장
            filters: 적용할 필터 목록 ["bollinger", "ma_alignment", "cup_handle"]

        Returns:
            TechnicalSignal or None
        """
        if df is None or len(df) < 30:
            return None

        if filters is None:
            filters = ["bollinger", "ma_alignment", "cup_handle"]

        current_price = df.iloc[-1]["Close"]

        # 각 분석기 실행
        bollinger_signal = None
        ma_alignment_signal = None
        cup_handle_signal = None

        if "bollinger" in filters:
            bollinger_signal = self.bollinger_analyzer.analyze(df, ticker, name, market)

        if "ma_alignment" in filters:
            ma_alignment_signal = self.ma_alignment_analyzer.analyze(df, ticker, name, market)

        if "cup_handle" in filters:
            cup_handle_signal = self.cup_handle_analyzer.analyze(df, ticker, name, market)

        # 개별 점수 추출
        bollinger_score = bollinger_signal.score if bollinger_signal else 0
        ma_alignment_score = ma_alignment_signal.score if ma_alignment_signal else 0
        cup_handle_score = cup_handle_signal.score if cup_handle_signal else 0

        # 활성 패턴 확인
        active_patterns = []
        if bollinger_score >= self.SCORE_THRESHOLDS["bollinger"]:
            active_patterns.append("bollinger_squeeze")
        if ma_alignment_score >= self.SCORE_THRESHOLDS["ma_alignment"]:
            active_patterns.append("ma_alignment")
        if cup_handle_score >= self.SCORE_THRESHOLDS["cup_handle"]:
            active_patterns.append("cup_handle")

        # 보너스 점수 계산 (다른 필터 충족 시)
        bonus_score = 0
        for pattern in active_patterns:
            if pattern == "bollinger_squeeze":
                bonus_score += self.BONUS_SCORES["bollinger"]
            elif pattern == "ma_alignment":
                bonus_score += self.BONUS_SCORES["ma_alignment"]
            elif pattern == "cup_handle":
                bonus_score += self.BONUS_SCORES["cup_handle"]

        # 통합 점수 (개별 점수 합 + 보너스)
        total_score = bollinger_score + ma_alignment_score + cup_handle_score + bonus_score

        return TechnicalSignal(
            ticker=ticker,
            name=name,
            market=market,
            current_price=round(current_price, 2),
            bollinger=bollinger_signal,
            ma_alignment=ma_alignment_signal,
            cup_handle=cup_handle_signal,
            total_score=total_score,
            active_patterns=active_patterns,
            bollinger_score=bollinger_score,
            ma_alignment_score=ma_alignment_score,
            cup_handle_score=cup_handle_score,
            bonus_score=bonus_score,
        )

    def analyze_stocks_batch(
        self,
        stocks_data: List[Tuple[str, str, pd.DataFrame]],
        filters: List[str] = None,
        max_workers: int = 10
    ) -> List[TechnicalSignal]:
        """
        여러 종목 배치 분석

        Args:
            stocks_data: [(ticker, name, DataFrame), ...] 또는 [(ticker, DataFrame), ...]
            filters: 적용할 필터 목록
            max_workers: 병렬 처리 워커 수

        Returns:
            TechnicalSignal 리스트
        """
        signals = []

        def analyze_single(item):
            if len(item) == 3:
                ticker, name, df = item
                market = "KR"  # 기본값
            else:
                ticker, df = item
                name = ticker
                market = "US"

            return self.analyze_stock(df, ticker, name, market, filters)

        with ThreadPoolExecutor(max_workers=max_workers) as executor:
            futures = {executor.submit(analyze_single, item): item for item in stocks_data}

            for future in as_completed(futures):
                result = future.result()
                if result:
                    signals.append(result)

        return signals

    def get_bollinger_squeeze_signals(
        self,
        signals: List[TechnicalSignal],
        min_score: int = 40
    ) -> List[TechnicalSignal]:
        """볼린저 스퀴즈 신호만 필터링"""
        filtered = [
            s for s in signals
            if s.bollinger and s.bollinger.score >= min_score
        ]
        return sorted(filtered, key=lambda x: x.bollinger.score, reverse=True)

    def get_ma_alignment_signals(
        self,
        signals: List[TechnicalSignal],
        min_score: int = 40
    ) -> List[TechnicalSignal]:
        """이평선 정배열 신호만 필터링"""
        filtered = [
            s for s in signals
            if s.ma_alignment and s.ma_alignment.score >= min_score
        ]
        return sorted(filtered, key=lambda x: x.ma_alignment.score, reverse=True)

    def get_cup_handle_signals(
        self,
        signals: List[TechnicalSignal],
        min_score: int = 40
    ) -> List[TechnicalSignal]:
        """컵앤핸들 패턴 신호만 필터링"""
        filtered = [
            s for s in signals
            if s.cup_handle and s.cup_handle.cup_detected and s.cup_handle.score >= min_score
        ]
        return sorted(filtered, key=lambda x: x.cup_handle.score, reverse=True)

    def filter_by_combine_mode(
        self,
        signals: List[TechnicalSignal],
        filters: List[str],
        combine_mode: str = "any",
        min_score: int = 40
    ) -> List[TechnicalSignal]:
        """
        조합 모드에 따른 필터링

        Args:
            signals: TechnicalSignal 리스트
            filters: 체크할 필터 목록
            combine_mode: "any" (OR) 또는 "all" (AND)
            min_score: 최소 점수

        Returns:
            필터링된 신호 리스트
        """
        filtered = []

        for signal in signals:
            passed_filters = []

            if "bollinger" in filters and signal.bollinger and signal.bollinger.score >= min_score:
                passed_filters.append("bollinger")

            if "ma_alignment" in filters and signal.ma_alignment and signal.ma_alignment.score >= min_score:
                passed_filters.append("ma_alignment")

            if "cup_handle" in filters and signal.cup_handle and signal.cup_handle.cup_detected and signal.cup_handle.score >= min_score:
                passed_filters.append("cup_handle")

            if combine_mode == "all":
                # AND: 모든 필터 통과
                if len(passed_filters) == len(filters):
                    filtered.append(signal)
            else:
                # OR: 하나 이상 통과
                if len(passed_filters) > 0:
                    filtered.append(signal)

        return sorted(filtered, key=lambda x: x.total_score, reverse=True)


def get_technical_service() -> TechnicalService:
    """TechnicalService 인스턴스 생성"""
    return TechnicalService()
