# -*- coding: utf-8 -*-
"""
CapEx Analyzer
자본적지출 분석기
"""
import logging
from typing import Optional, List
import numpy as np

from app.services.fundamental_analysis.base_fundamental_analyzer import BaseFundamentalAnalyzer
from app.models.fundamental_models import FundamentalData, CapExSignal

logger = logging.getLogger(__name__)


class CapExAnalyzer(BaseFundamentalAnalyzer):
    """
    CapEx (Capital Expenditure) 분석기 (최대 20점)

    점수 계산:
    - CapEx/순이익 < 15%: +15점
    - CapEx/순이익 < 25% (15% 이상): +10점
    - CapEx/순이익 < 35% (25% 이상): +5점
    - CapEx/순이익 >= 50%: -10점
    - 3년 평균 대비 안정적: +5점
    """

    # CapEx 비율 기준
    CAPEX_EXCELLENT = 15.0  # 우수: 15% 미만
    CAPEX_GOOD = 25.0  # 양호: 25% 미만
    CAPEX_FAIR = 35.0  # 보통: 35% 미만
    CAPEX_POOR = 50.0  # 위험: 50% 이상

    # 안정성 기준 (3년 평균 대비 변동폭)
    STABILITY_THRESHOLD = 0.20  # 20% 이내

    @property
    def name(self) -> str:
        return "capex"

    @property
    def max_score(self) -> int:
        return 20

    @property
    def min_years_required(self) -> int:
        return 1  # 최소 1년

    def analyze(
        self,
        data: FundamentalData,
        ticker: str,
        name: str = "",
        market: str = "US"
    ) -> Optional[CapExSignal]:
        """
        CapEx 분석 수행

        Returns:
            CapExSignal 또는 None
        """
        try:
            if not self.has_sufficient_data(data):
                return None

            # CapEx 및 순이익 데이터 추출
            capex_data = data.capex_data
            net_income_data = data.net_income_data

            if not capex_data or not net_income_data:
                return None

            # 공통 연도 찾기
            common_years = sorted(set(capex_data.keys()) & set(net_income_data.keys()))
            if not common_years:
                return None

            # 연도별 CapEx/순이익 비율 계산
            ratio_history = []
            for year in common_years:
                capex = capex_data[year]
                net_income = net_income_data[year]
                if net_income > 0:
                    ratio = (capex / net_income) * 100
                    ratio_history.append((year, ratio))

            if not ratio_history:
                return None

            # 현재(최근) 데이터
            latest_year = max(y for y, _ in ratio_history)
            current_ratio = next(r for y, r in ratio_history if y == latest_year)
            current_capex = capex_data[latest_year]
            current_net_income = net_income_data[latest_year]

            # 3년 평균 계산
            ratio_values = [r for _, r in ratio_history]
            recent_3_ratios = ratio_values[-3:] if len(ratio_values) >= 3 else ratio_values
            ratio_3y_avg = np.mean(recent_3_ratios)

            # 조건 판단
            capex_below_15 = current_ratio < self.CAPEX_EXCELLENT
            capex_below_25 = current_ratio < self.CAPEX_GOOD
            capex_below_35 = current_ratio < self.CAPEX_FAIR
            capex_above_50 = current_ratio >= self.CAPEX_POOR

            # 안정성 판단 (3년 평균 대비 20% 이내)
            is_stable = False
            if ratio_3y_avg > 0:
                deviation = abs(current_ratio - ratio_3y_avg) / ratio_3y_avg
                is_stable = deviation <= self.STABILITY_THRESHOLD

            # 점수 계산
            score = self._calculate_score(
                capex_below_15=capex_below_15,
                capex_below_25=capex_below_25,
                capex_below_35=capex_below_35,
                capex_above_50=capex_above_50,
                is_stable=is_stable,
            )

            return CapExSignal(
                current_capex=current_capex,
                current_net_income=current_net_income,
                capex_to_income_ratio=round(current_ratio, 2),
                capex_ratio_history=[round(r, 2) for _, r in ratio_history],
                capex_ratio_3y_avg=round(ratio_3y_avg, 2),
                years_available=len(ratio_history),
                capex_below_15=capex_below_15,
                capex_below_25=capex_below_25,
                capex_below_35=capex_below_35,
                capex_above_50=capex_above_50,
                is_stable=is_stable,
                score=score,
            )

        except Exception as e:
            logger.debug(f"CapEx 분석 실패 {ticker}: {e}")
            return None

    def _calculate_score(
        self,
        capex_below_15: bool,
        capex_below_25: bool,
        capex_below_35: bool,
        capex_above_50: bool,
        is_stable: bool,
    ) -> int:
        """
        점수 계산 (최대 20점)

        - CapEx 비율 수준: -10~15점
        - 안정성: +5점
        """
        score = 0

        # CapEx 비율 수준 점수 (중복 불가)
        if capex_above_50:
            score -= 10
        elif capex_below_15:
            score += 15
        elif capex_below_25:
            score += 10
        elif capex_below_35:
            score += 5

        # 안정성 점수
        if is_stable:
            score += 5

        return max(0, min(score, self.max_score))


def get_capex_analyzer() -> CapExAnalyzer:
    """CapExAnalyzer 인스턴스 생성"""
    return CapExAnalyzer()
