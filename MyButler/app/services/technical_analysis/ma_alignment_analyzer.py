# -*- coding: utf-8 -*-
"""
MA Alignment Analyzer
이동평균선 정배열 & 골든크로스 분석기
"""
import logging
from typing import Optional

import pandas as pd
import numpy as np

from app.services.technical_analysis.base_analyzer import BaseAnalyzer
from app.models.technical_models import MAAlignmentSignal

logger = logging.getLogger(__name__)


class MAAlignmentAnalyzer(BaseAnalyzer):
    """이동평균선 정배열 분석기"""

    # 이동평균 기간
    SMA_5 = 5
    SMA_20 = 20
    SMA_60 = 60
    SMA_120 = 120

    # 이격도 기준
    DISPARITY_OPTIMAL_MIN = 5.0  # 적정 이격도 최소
    DISPARITY_OPTIMAL_MAX = 15.0  # 적정 이격도 최대
    DISPARITY_OVERHEATED = 15.0  # 과열 이격도

    # 골든크로스 감지 기간
    GC_LOOKBACK = 5  # 최근 5일

    @property
    def name(self) -> str:
        return "ma_alignment"

    @property
    def min_data_length(self) -> int:
        return 130  # 120일 이평 + 여유분

    def calculate_moving_averages(self, df: pd.DataFrame) -> pd.DataFrame:
        """이동평균 계산"""
        df = df.copy()

        df["sma_5"] = df["Close"].rolling(window=self.SMA_5).mean()
        df["sma_20"] = df["Close"].rolling(window=self.SMA_20).mean()
        df["sma_60"] = df["Close"].rolling(window=self.SMA_60).mean()
        df["sma_120"] = df["Close"].rolling(window=self.SMA_120).mean()

        # 이격도 (SMA_20 기준)
        df["disparity"] = ((df["Close"] - df["sma_20"]) / df["sma_20"]) * 100

        return df

    def analyze(
        self,
        df: pd.DataFrame,
        ticker: str,
        name: str = "",
        market: str = "US"
    ) -> Optional[MAAlignmentSignal]:
        """
        이동평균선 정배열 분석

        신호 조건:
        - 완전 정배열 (Price > 5 > 20 > 60 > 120): +40점
        - 부분 정배열 (3단계): +25점
        - 단기 골든크로스 (5/20): +10점
        - 중기 골든크로스 (20/60): +15점
        - 장기 골든크로스 (60/120): +20점
        - 이격도 적정 (5~15%): +10점
        - 이격도 과열 (>15%): -20점

        최대 점수: 95점
        """
        try:
            if not self.has_sufficient_data(df):
                return None

            # 이동평균 계산
            df = self.calculate_moving_averages(df)

            # 현재 데이터
            current = df.iloc[-1]
            current_price = current["Close"]

            # NaN 체크
            if pd.isna(current["sma_120"]):
                return None

            sma_5 = current["sma_5"]
            sma_20 = current["sma_20"]
            sma_60 = current["sma_60"]
            sma_120 = current["sma_120"]
            disparity = current["disparity"]

            # 정배열 체크
            alignment_checks = [
                current_price > sma_5,
                sma_5 > sma_20,
                sma_20 > sma_60,
                sma_60 > sma_120,
            ]
            alignment_count = sum(alignment_checks)
            is_perfect_alignment = alignment_count == 4
            is_partial_alignment = alignment_count >= 3

            # 골든크로스 감지
            golden_cross_5_20 = self._detect_golden_cross(df, "sma_5", "sma_20")
            golden_cross_20_60 = self._detect_golden_cross(df, "sma_20", "sma_60")
            golden_cross_60_120 = self._detect_golden_cross(df, "sma_60", "sma_120")

            # 이격도 상태
            disparity_optimal = self.DISPARITY_OPTIMAL_MIN <= disparity <= self.DISPARITY_OPTIMAL_MAX
            disparity_overheated = disparity > self.DISPARITY_OVERHEATED

            # 점수 계산
            score = self._calculate_score(
                is_perfect_alignment=is_perfect_alignment,
                is_partial_alignment=is_partial_alignment,
                golden_cross_5_20=golden_cross_5_20,
                golden_cross_20_60=golden_cross_20_60,
                golden_cross_60_120=golden_cross_60_120,
                disparity_optimal=disparity_optimal,
                disparity_overheated=disparity_overheated
            )

            return MAAlignmentSignal(
                sma_5=round(sma_5, 2),
                sma_20=round(sma_20, 2),
                sma_60=round(sma_60, 2),
                sma_120=round(sma_120, 2),
                disparity=round(disparity, 2),
                is_perfect_alignment=is_perfect_alignment,
                is_partial_alignment=is_partial_alignment,
                alignment_count=alignment_count,
                golden_cross_5_20=golden_cross_5_20,
                golden_cross_20_60=golden_cross_20_60,
                golden_cross_60_120=golden_cross_60_120,
                disparity_optimal=disparity_optimal,
                disparity_overheated=disparity_overheated,
                score=score,
            )

        except Exception as e:
            logger.debug(f"이동평균 정배열 분석 실패 {ticker}: {e}")
            return None

    def _detect_golden_cross(
        self,
        df: pd.DataFrame,
        fast_col: str,
        slow_col: str
    ) -> bool:
        """골든크로스 감지 (최근 5일 내)"""
        if len(df) < self.GC_LOOKBACK + 1:
            return False

        for i in range(1, self.GC_LOOKBACK + 1):
            idx = -i
            prev_idx = -i - 1

            current = df.iloc[idx]
            previous = df.iloc[prev_idx]

            # NaN 체크
            if pd.isna(current[fast_col]) or pd.isna(current[slow_col]):
                continue
            if pd.isna(previous[fast_col]) or pd.isna(previous[slow_col]):
                continue

            # 이전에는 fast < slow, 현재는 fast > slow
            was_below = previous[fast_col] <= previous[slow_col]
            now_above = current[fast_col] > current[slow_col]

            if was_below and now_above:
                return True

        return False

    def _calculate_score(
        self,
        is_perfect_alignment: bool,
        is_partial_alignment: bool,
        golden_cross_5_20: bool,
        golden_cross_20_60: bool,
        golden_cross_60_120: bool,
        disparity_optimal: bool,
        disparity_overheated: bool
    ) -> int:
        """
        점수 계산 (최대 95점)

        - 완전 정배열: +40점
        - 부분 정배열: +25점 (완전 정배열과 중복 불가)
        - 단기 GC (5/20): +10점
        - 중기 GC (20/60): +15점
        - 장기 GC (60/120): +20점
        - 이격도 적정: +10점
        - 이격도 과열: -20점
        """
        score = 0

        # 정배열 점수 (중복 불가)
        if is_perfect_alignment:
            score += 40
        elif is_partial_alignment:
            score += 25

        # 골든크로스 점수
        if golden_cross_5_20:
            score += 10
        if golden_cross_20_60:
            score += 15
        if golden_cross_60_120:
            score += 20

        # 이격도 점수
        if disparity_overheated:
            score -= 20
        elif disparity_optimal:
            score += 10

        return max(-100, min(score, 95))


def get_ma_alignment_analyzer() -> MAAlignmentAnalyzer:
    """MAAlignmentAnalyzer 인스턴스 생성"""
    return MAAlignmentAnalyzer()
