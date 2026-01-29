# -*- coding: utf-8 -*-
"""
Debt Analyzer
부채비율 분석기
"""
import logging
from typing import Optional

from app.services.fundamental_analysis.base_fundamental_analyzer import BaseFundamentalAnalyzer
from app.models.fundamental_models import FundamentalData, DebtSignal

logger = logging.getLogger(__name__)


class DebtAnalyzer(BaseFundamentalAnalyzer):
    """
    부채비율 분석기 (최대 25점)

    점수 계산:
    - 부채비율 <= 50%: +15점
    - 부채비율 <= 100% (50% 초과): +10점
    - 부채비율 <= 150% (100% 초과): +5점
    - 부채비율 > 200%: -10점
    - 순이익/부채 >= 20% (5년 내 상환): +10점
    - 순이익/부채 >= 10% (10년 내 상환): +5점
    """

    # 부채비율 기준
    DEBT_EXCELLENT = 50.0  # 우수: 50% 이하
    DEBT_GOOD = 100.0  # 양호: 100% 이하
    DEBT_FAIR = 150.0  # 보통: 150% 이하
    DEBT_POOR = 200.0  # 위험: 200% 초과

    # 상환 능력 기준
    REPAY_5_YEARS = 20.0  # 5년 내 상환: 순이익/부채 >= 20%
    REPAY_10_YEARS = 10.0  # 10년 내 상환: 순이익/부채 >= 10%

    @property
    def name(self) -> str:
        return "debt"

    @property
    def max_score(self) -> int:
        return 25

    @property
    def min_years_required(self) -> int:
        return 1  # 최소 1년 (현재 데이터만 필요)

    def analyze(
        self,
        data: FundamentalData,
        ticker: str,
        name: str = "",
        market: str = "US"
    ) -> Optional[DebtSignal]:
        """
        부채비율 분석 수행

        Returns:
            DebtSignal 또는 None
        """
        try:
            if not self.has_sufficient_data(data):
                return None

            # 부채 데이터 추출
            total_debt = data.total_debt
            total_equity = data.total_equity
            net_income = data.net_income

            # 부채비율 계산
            if total_equity <= 0:
                # 자본잠식 상태
                debt_ratio = 999.9
            else:
                debt_ratio = (total_debt / total_equity) * 100

            # 상환 비율 계산
            repayment_ratio = 0.0
            years_to_repay = float('inf')
            if total_debt > 0 and net_income > 0:
                repayment_ratio = (net_income / total_debt) * 100
                years_to_repay = total_debt / net_income

            # 조건 판단
            debt_below_50 = debt_ratio <= self.DEBT_EXCELLENT
            debt_below_100 = debt_ratio <= self.DEBT_GOOD
            debt_below_150 = debt_ratio <= self.DEBT_FAIR
            debt_above_200 = debt_ratio > self.DEBT_POOR

            can_repay_in_5_years = repayment_ratio >= self.REPAY_5_YEARS
            can_repay_in_10_years = repayment_ratio >= self.REPAY_10_YEARS

            # 점수 계산
            score = self._calculate_score(
                debt_below_50=debt_below_50,
                debt_below_100=debt_below_100,
                debt_below_150=debt_below_150,
                debt_above_200=debt_above_200,
                can_repay_in_5_years=can_repay_in_5_years,
                can_repay_in_10_years=can_repay_in_10_years,
            )

            return DebtSignal(
                current_debt_ratio=round(debt_ratio, 2),
                total_debt=total_debt,
                net_income=net_income,
                repayment_ratio=round(repayment_ratio, 2),
                years_to_repay=round(years_to_repay, 1) if years_to_repay != float('inf') else 999.9,
                debt_below_50=debt_below_50,
                debt_below_100=debt_below_100,
                debt_below_150=debt_below_150,
                debt_above_200=debt_above_200,
                can_repay_in_5_years=can_repay_in_5_years,
                can_repay_in_10_years=can_repay_in_10_years,
                score=score,
            )

        except Exception as e:
            logger.debug(f"부채 분석 실패 {ticker}: {e}")
            return None

    def _calculate_score(
        self,
        debt_below_50: bool,
        debt_below_100: bool,
        debt_below_150: bool,
        debt_above_200: bool,
        can_repay_in_5_years: bool,
        can_repay_in_10_years: bool,
    ) -> int:
        """
        점수 계산 (최대 25점)

        - 부채비율 수준: -10~15점
        - 상환 능력: 0~10점
        """
        score = 0

        # 부채비율 수준 점수 (중복 불가)
        if debt_above_200:
            score -= 10
        elif debt_below_50:
            score += 15
        elif debt_below_100:
            score += 10
        elif debt_below_150:
            score += 5

        # 상환 능력 점수 (중복 불가)
        if can_repay_in_5_years:
            score += 10
        elif can_repay_in_10_years:
            score += 5

        return max(0, min(score, self.max_score))


def get_debt_analyzer() -> DebtAnalyzer:
    """DebtAnalyzer 인스턴스 생성"""
    return DebtAnalyzer()
