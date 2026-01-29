# -*- coding: utf-8 -*-
"""
GPM Analyzer
매출총이익률 분석기
"""
import logging
from typing import Optional, List

from app.services.fundamental_analysis.base_fundamental_analyzer import BaseFundamentalAnalyzer
from app.models.fundamental_models import FundamentalData, GPMSignal

logger = logging.getLogger(__name__)


class GPMAnalyzer(BaseFundamentalAnalyzer):
    """
    GPM (Gross Profit Margin) 분석기 (최대 25점)

    점수 계산:
    - GPM >= 50%: +15점
    - GPM >= 40% (50% 미만): +10점
    - GPM >= 30% (40% 미만): +5점
    - 3년 연속 유지/상승: +10점
    """

    # GPM 기준
    GPM_EXCELLENT = 50.0  # 우수: 50% 이상
    GPM_GOOD = 40.0  # 양호: 40% 이상
    GPM_FAIR = 30.0  # 보통: 30% 이상

    @property
    def name(self) -> str:
        return "gpm"

    @property
    def max_score(self) -> int:
        return 25

    @property
    def min_years_required(self) -> int:
        return 1  # 최소 1년

    def analyze(
        self,
        data: FundamentalData,
        ticker: str,
        name: str = "",
        market: str = "US"
    ) -> Optional[GPMSignal]:
        """
        GPM 분석 수행

        Returns:
            GPMSignal 또는 None
        """
        try:
            if not self.has_sufficient_data(data):
                return None

            # GPM 데이터 추출 (연도 정렬)
            gpm_data = data.gpm_data
            if not gpm_data or len(gpm_data) < self.min_years_required:
                return None

            # 연도순 정렬 (오래된 것부터)
            sorted_years = sorted(gpm_data.keys())
            gpm_history = [gpm_data[year] for year in sorted_years]

            # 현재(최근) GPM
            current_gpm = gpm_history[-1]

            # 조건 판단
            gpm_above_50 = current_gpm >= self.GPM_EXCELLENT
            gpm_above_40 = current_gpm >= self.GPM_GOOD
            gpm_above_30 = current_gpm >= self.GPM_FAIR

            # 3년 연속 유지/상승 여부
            three_year_stable_or_rising = self._check_three_year_stability(gpm_history)

            # 점수 계산
            score = self._calculate_score(
                gpm_above_50=gpm_above_50,
                gpm_above_40=gpm_above_40,
                gpm_above_30=gpm_above_30,
                three_year_stable_or_rising=three_year_stable_or_rising,
            )

            return GPMSignal(
                current_gpm=round(current_gpm, 2),
                gpm_history=[round(g, 2) for g in gpm_history],
                years_available=len(gpm_history),
                gpm_above_50=gpm_above_50,
                gpm_above_40=gpm_above_40,
                gpm_above_30=gpm_above_30,
                three_year_stable_or_rising=three_year_stable_or_rising,
                score=score,
            )

        except Exception as e:
            logger.debug(f"GPM 분석 실패 {ticker}: {e}")
            return None

    def _check_three_year_stability(self, gpm_history: List[float]) -> bool:
        """
        3년 연속 유지/상승 여부 확인

        조건: 최근 3년간 GPM이 감소하지 않거나, 감소폭이 2%p 이내
        """
        if len(gpm_history) < 3:
            return False

        recent_3 = gpm_history[-3:]

        # 각 연도별 비교 (전년 대비 2%p 이상 하락 없음)
        for i in range(1, len(recent_3)):
            if recent_3[i] < recent_3[i - 1] - 2:  # 2%p 이상 하락
                return False

        return True

    def _calculate_score(
        self,
        gpm_above_50: bool,
        gpm_above_40: bool,
        gpm_above_30: bool,
        three_year_stable_or_rising: bool,
    ) -> int:
        """
        점수 계산 (최대 25점)

        - GPM 수준: 5~15점
        - 3년 연속 유지/상승: +10점
        """
        score = 0

        # GPM 수준 점수 (중복 불가)
        if gpm_above_50:
            score += 15
        elif gpm_above_40:
            score += 10
        elif gpm_above_30:
            score += 5

        # 3년 연속 유지/상승
        if three_year_stable_or_rising:
            score += 10

        return min(score, self.max_score)


def get_gpm_analyzer() -> GPMAnalyzer:
    """GPMAnalyzer 인스턴스 생성"""
    return GPMAnalyzer()
