# -*- coding: utf-8 -*-
"""
Cup and Handle Analyzer
컵 앤 핸들 패턴 분석기
"""
import logging
from typing import Optional, Tuple
from datetime import datetime

import pandas as pd
import numpy as np

from app.services.technical_analysis.base_analyzer import BaseAnalyzer
from app.models.technical_models import CupHandleSignal

logger = logging.getLogger(__name__)


class CupHandleAnalyzer(BaseAnalyzer):
    """컵 앤 핸들 패턴 분석기"""

    # 컵 패턴 조건
    CUP_MIN_DURATION = 60  # 최소 60일 (3개월)
    CUP_MAX_DURATION = 130  # 최대 130일 (6개월)
    CUP_MIN_DEPTH = 15.0  # 최소 15% 하락
    CUP_MAX_DEPTH = 40.0  # 최대 40% 하락
    RIGHT_PEAK_MIN_RATIO = 0.90  # 우측 고점 최소 (좌측 대비 90%)
    RIGHT_PEAK_MAX_RATIO = 1.10  # 우측 고점 최대 (좌측 대비 110%)

    # 핸들 조건
    HANDLE_MIN_DEPTH = 5.0  # 최소 5% 눌림
    HANDLE_MAX_DEPTH = 15.0  # 최대 15% 눌림

    # 돌파 조건
    BREAKOUT_IMMINENT_THRESHOLD = 0.97  # 전고점의 97% 이내
    BREAKOUT_CONFIRMED_THRESHOLD = 1.00  # 전고점 상회

    # 거래량 기준
    VOLUME_SURGE_RATIO = 2.0  # 2배 이상

    @property
    def name(self) -> str:
        return "cup_handle"

    @property
    def min_data_length(self) -> int:
        return 150  # 130일 + 여유분

    def analyze(
        self,
        df: pd.DataFrame,
        ticker: str,
        name: str = "",
        market: str = "US"
    ) -> Optional[CupHandleSignal]:
        """
        컵 앤 핸들 패턴 분석

        신호 조건:
        - 컵 패턴 감지: +25점
        - 핸들 패턴 감지: +15점
        - 돌파 임박 (전고점 -3% 이내): +15점
        - 돌파 확정 (전고점 상회): +25점
        - 거래량 2배 이상: +20점

        최대 점수: 100점
        """
        try:
            if not self.has_sufficient_data(df):
                return None

            current_price = df.iloc[-1]["Close"]

            # 컵 패턴 탐색
            cup_result = self._find_cup_pattern(df)

            if cup_result is None:
                # 컵 패턴 없음
                return CupHandleSignal(
                    cup_detected=False,
                    current_price=round(current_price, 2),
                    score=0
                )

            (cup_start_idx, cup_bottom_idx, cup_end_idx,
             left_peak, cup_bottom, right_peak, cup_depth, cup_duration) = cup_result

            # 날짜 문자열 변환
            cup_start_date = self._idx_to_date_str(df, cup_start_idx)
            cup_bottom_date = self._idx_to_date_str(df, cup_bottom_idx)
            cup_end_date = self._idx_to_date_str(df, cup_end_idx)

            # 핸들 패턴 탐색
            handle_result = self._find_handle_pattern(df, cup_end_idx, right_peak)

            handle_detected = handle_result is not None
            handle_depth = handle_result if handle_result else 0.0

            # 돌파 상태 확인
            resistance_price = max(left_peak, right_peak)
            breakout_imminent = current_price >= resistance_price * self.BREAKOUT_IMMINENT_THRESHOLD
            breakout_confirmed = current_price >= resistance_price * self.BREAKOUT_CONFIRMED_THRESHOLD

            # 거래량 확인
            volume_ma = df["Volume"].tail(20).mean()
            current_volume = df.iloc[-1]["Volume"]
            volume_ratio = current_volume / volume_ma if volume_ma > 0 else 0
            volume_surge = volume_ratio >= self.VOLUME_SURGE_RATIO

            # 점수 계산
            score = self._calculate_score(
                cup_detected=True,
                handle_detected=handle_detected,
                breakout_imminent=breakout_imminent,
                breakout_confirmed=breakout_confirmed,
                volume_surge=volume_surge
            )

            return CupHandleSignal(
                cup_detected=True,
                cup_start_date=cup_start_date,
                cup_bottom_date=cup_bottom_date,
                cup_end_date=cup_end_date,
                cup_depth_percent=round(cup_depth, 2),
                cup_duration_days=cup_duration,
                handle_detected=handle_detected,
                handle_depth_percent=round(handle_depth, 2),
                left_peak_price=round(left_peak, 2),
                cup_bottom_price=round(cup_bottom, 2),
                right_peak_price=round(right_peak, 2),
                current_price=round(current_price, 2),
                breakout_imminent=breakout_imminent,
                breakout_confirmed=breakout_confirmed,
                volume_ratio=round(volume_ratio, 2),
                volume_surge=volume_surge,
                score=score,
            )

        except Exception as e:
            logger.debug(f"컵앤핸들 분석 실패 {ticker}: {e}")
            return None

    def _find_cup_pattern(
        self,
        df: pd.DataFrame
    ) -> Optional[Tuple[int, int, int, float, float, float, float, int]]:
        """
        컵 패턴 탐색

        Returns:
            (cup_start_idx, cup_bottom_idx, cup_end_idx,
             left_peak_price, cup_bottom_price, right_peak_price,
             cup_depth_percent, cup_duration_days) or None
        """
        if len(df) < self.CUP_MIN_DURATION:
            return None

        closes = df["Close"].values
        highs = df["High"].values

        # 최근 데이터에서 역순으로 컵 패턴 탐색
        # 탐색 범위: 최근 CUP_MAX_DURATION + 20일
        search_range = min(len(df), self.CUP_MAX_DURATION + 20)

        best_cup = None
        best_score = 0

        # 가능한 컵 시작점 탐색
        for start_offset in range(self.CUP_MIN_DURATION, search_range):
            start_idx = len(df) - start_offset - 1

            if start_idx < 0:
                break

            # 좌측 고점: 시작 부근의 고점
            left_region_start = max(0, start_idx - 5)
            left_region_end = min(len(df), start_idx + 10)
            left_peak_local_idx = np.argmax(highs[left_region_start:left_region_end])
            left_peak_idx = left_region_start + left_peak_local_idx
            left_peak = highs[left_peak_idx]

            # 가능한 컵 기간 내에서 바닥 탐색
            for duration in range(self.CUP_MIN_DURATION, min(start_offset, self.CUP_MAX_DURATION) + 1):
                end_idx = start_idx + duration
                if end_idx >= len(df):
                    continue

                # 바닥점 탐색 (좌측 고점 ~ 현재 사이)
                search_start = left_peak_idx + 5
                search_end = end_idx - 5
                if search_end <= search_start:
                    continue

                bottom_local_idx = np.argmin(closes[search_start:search_end])
                bottom_idx = search_start + bottom_local_idx
                cup_bottom = closes[bottom_idx]

                # 컵 깊이 체크
                cup_depth = ((left_peak - cup_bottom) / left_peak) * 100
                if cup_depth < self.CUP_MIN_DEPTH or cup_depth > self.CUP_MAX_DEPTH:
                    continue

                # 우측 고점 탐색 (바닥 ~ 끝 사이)
                right_region_start = bottom_idx + 5
                right_region_end = min(len(df), end_idx + 5)
                if right_region_end <= right_region_start:
                    continue

                right_peak_local_idx = np.argmax(highs[right_region_start:right_region_end])
                right_peak_idx = right_region_start + right_peak_local_idx
                right_peak = highs[right_peak_idx]

                # 우측 고점 비율 체크
                right_ratio = right_peak / left_peak
                if right_ratio < self.RIGHT_PEAK_MIN_RATIO or right_ratio > self.RIGHT_PEAK_MAX_RATIO:
                    continue

                # U자형 확인 (바닥이 좌/우 고점보다 낮아야 함)
                if cup_bottom >= left_peak * 0.9 or cup_bottom >= right_peak * 0.9:
                    continue

                # 컵 패턴 점수 계산 (더 완벽한 U자형일수록 높은 점수)
                symmetry_score = 1 - abs(right_ratio - 1.0)  # 좌우 대칭
                depth_score = 1 - abs(cup_depth - 25) / 25  # 25% 깊이가 이상적
                pattern_score = symmetry_score * depth_score

                if pattern_score > best_score:
                    best_score = pattern_score
                    best_cup = (
                        left_peak_idx, bottom_idx, right_peak_idx,
                        left_peak, cup_bottom, right_peak,
                        cup_depth, duration
                    )

        return best_cup

    def _find_handle_pattern(
        self,
        df: pd.DataFrame,
        cup_end_idx: int,
        right_peak: float
    ) -> Optional[float]:
        """
        핸들 패턴 탐색

        Returns:
            handle_depth_percent or None
        """
        if cup_end_idx >= len(df) - 5:
            return None

        # 핸들 영역: 컵 끝 ~ 현재
        handle_region = df.iloc[cup_end_idx:]
        if len(handle_region) < 5:
            return None

        # 핸들 최저점
        handle_low = handle_region["Low"].min()

        # 핸들 깊이 계산
        handle_depth = ((right_peak - handle_low) / right_peak) * 100

        # 핸들 깊이 조건 확인
        if self.HANDLE_MIN_DEPTH <= handle_depth <= self.HANDLE_MAX_DEPTH:
            return handle_depth

        return None

    def _idx_to_date_str(self, df: pd.DataFrame, idx: int) -> str:
        """인덱스를 날짜 문자열로 변환"""
        try:
            date = df.index[idx]
            if hasattr(date, 'strftime'):
                return date.strftime("%Y-%m-%d")
            return str(date)
        except:
            return ""

    def _calculate_score(
        self,
        cup_detected: bool,
        handle_detected: bool,
        breakout_imminent: bool,
        breakout_confirmed: bool,
        volume_surge: bool
    ) -> int:
        """
        점수 계산 (최대 100점)

        - 컵 패턴 감지: +25점
        - 핸들 패턴 감지: +15점
        - 돌파 임박: +15점 / 돌파 확정: +25점 (중복 불가)
        - 거래량 급증: +20점
        """
        score = 0

        if cup_detected:
            score += 25

        if handle_detected:
            score += 15

        # 돌파 점수 (중복 불가)
        if breakout_confirmed:
            score += 25
        elif breakout_imminent:
            score += 15

        if volume_surge:
            score += 20

        return min(score, 100)


def get_cup_handle_analyzer() -> CupHandleAnalyzer:
    """CupHandleAnalyzer 인스턴스 생성"""
    return CupHandleAnalyzer()
