# -*- coding: utf-8 -*-
"""
ROE Analyzer
자기자본이익률 분석기
"""
import logging
from typing import Optional, List
import numpy as np

from app.services.fundamental_analysis.base_fundamental_analyzer import BaseFundamentalAnalyzer
from app.models.fundamental_models import FundamentalData, ROESignal

logger = logging.getLogger(__name__)


class ROEAnalyzer(BaseFundamentalAnalyzer):
    """
    ROE 분석기 (최대 30점)

    점수 계산:
    - ROE >= 20%: +15점
    - ROE >= 15% (20% 미만): +10점
    - ROE >= 10% (15% 미만): +5점
    - 10년 표준편차 <= 3%: +10점
    - 10년 표준편차 <= 5% (3% 초과): +5점
    - 추세 상승: +5점
    - 추세 하락: -5점
    """

    # ROE 기준
    ROE_EXCELLENT = 20.0  # 우수: 20% 이상
    ROE_GOOD = 15.0  # 양호: 15% 이상
    ROE_FAIR = 10.0  # 보통: 10% 이상

    # 일관성 기준 (표준편차)
    STD_HIGHLY_CONSISTENT = 3.0  # 매우 일관적: 3% 이하
    STD_CONSISTENT = 5.0  # 일관적: 5% 이하

    @property
    def name(self) -> str:
        return "roe"

    @property
    def max_score(self) -> int:
        return 30

    @property
    def min_years_required(self) -> int:
        return 3  # 최소 3년

    def analyze(
        self,
        data: FundamentalData,
        ticker: str,
        name: str = "",
        market: str = "US"
    ) -> Optional[ROESignal]:
        """
        ROE 분석 수행

        Returns:
            ROESignal 또는 None
        """
        try:
            if not self.has_sufficient_data(data):
                return None

            # ROE 데이터 추출 (연도 정렬)
            roe_data = data.roe_data
            if not roe_data or len(roe_data) < self.min_years_required:
                return None

            # 연도순 정렬 (오래된 것부터)
            sorted_years = sorted(roe_data.keys())
            roe_history = [roe_data[year] for year in sorted_years]

            # 현재(최근) ROE
            current_roe = roe_history[-1]

            # 통계 계산
            roe_mean = np.mean(roe_history)
            roe_std = np.std(roe_history) if len(roe_history) > 1 else 0

            # 조건 판단
            roe_above_20 = current_roe >= self.ROE_EXCELLENT
            roe_above_15 = current_roe >= self.ROE_GOOD
            roe_above_10 = current_roe >= self.ROE_FAIR

            is_highly_consistent = roe_std <= self.STD_HIGHLY_CONSISTENT
            is_consistent = roe_std <= self.STD_CONSISTENT

            # 추세 분석 (최근 3년 또는 전체)
            trend_direction, trend_score = self._analyze_trend(roe_history)

            # 점수 계산
            score = self._calculate_score(
                current_roe=current_roe,
                roe_above_20=roe_above_20,
                roe_above_15=roe_above_15,
                roe_above_10=roe_above_10,
                is_highly_consistent=is_highly_consistent,
                is_consistent=is_consistent,
                trend_score=trend_score,
                years_available=len(roe_history)
            )

            return ROESignal(
                current_roe=round(current_roe, 2),
                roe_history=[round(r, 2) for r in roe_history],
                roe_mean=round(roe_mean, 2),
                roe_std=round(roe_std, 2),
                years_available=len(roe_history),
                roe_above_20=roe_above_20,
                roe_above_15=roe_above_15,
                roe_above_10=roe_above_10,
                is_highly_consistent=is_highly_consistent,
                is_consistent=is_consistent,
                trend_direction=trend_direction,
                trend_score=trend_score,
                score=score,
            )

        except Exception as e:
            logger.debug(f"ROE 분석 실패 {ticker}: {e}")
            return None

    def _analyze_trend(self, roe_history: List[float]) -> tuple:
        """
        ROE 추세 분석

        Returns:
            (trend_direction, trend_score)
        """
        if len(roe_history) < 2:
            return "neutral", 0

        # 최근 3년 데이터 사용 (있으면)
        recent = roe_history[-3:] if len(roe_history) >= 3 else roe_history

        # 선형 회귀 대신 단순 비교
        first = recent[0]
        last = recent[-1]

        if last > first + 2:  # 2%p 이상 상승
            return "up", 5
        elif last < first - 2:  # 2%p 이상 하락
            return "down", -5
        else:
            return "neutral", 0

    def _calculate_score(
        self,
        current_roe: float,
        roe_above_20: bool,
        roe_above_15: bool,
        roe_above_10: bool,
        is_highly_consistent: bool,
        is_consistent: bool,
        trend_score: int,
        years_available: int
    ) -> int:
        """
        점수 계산 (최대 30점)

        - ROE 수준: 5~15점
        - 일관성: 0~10점
        - 추세: -5~+5점
        """
        score = 0

        # ROE 수준 점수 (중복 불가)
        if roe_above_20:
            score += 15
        elif roe_above_15:
            score += 10
        elif roe_above_10:
            score += 5

        # 일관성 점수 (중복 불가, 최소 5년 데이터 필요)
        if years_available >= 5:
            if is_highly_consistent:
                score += 10
            elif is_consistent:
                score += 5

        # 추세 점수
        score += trend_score

        return max(0, min(score, self.max_score))


def get_roe_analyzer() -> ROEAnalyzer:
    """ROEAnalyzer 인스턴스 생성"""
    return ROEAnalyzer()
