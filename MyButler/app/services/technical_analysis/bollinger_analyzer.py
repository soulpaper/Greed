# -*- coding: utf-8 -*-
"""
Bollinger Analyzer
볼린저 밴드 스퀴즈 & 거래량 분석기
"""
import logging
from typing import Optional

import pandas as pd
import numpy as np

from app.services.technical_analysis.base_analyzer import BaseAnalyzer
from app.models.technical_models import BollingerSignal

logger = logging.getLogger(__name__)


class BollingerAnalyzer(BaseAnalyzer):
    """볼린저 밴드 스퀴즈 분석기"""

    # 볼린저 밴드 설정
    BB_PERIOD = 20  # 기간
    BB_STD = 2  # 표준편차 배수

    # 스퀴즈 판단 기준
    SQUEEZE_PERCENTILE = 20  # 하위 20%
    STRONG_SQUEEZE_PERCENTILE = 10  # 하위 10%

    # 거래량 기준
    VOLUME_SURGE_RATIO = 2.0  # 2배
    STRONG_VOLUME_SURGE_RATIO = 3.0  # 3배

    # 돌파 시도 기준
    BREAKOUT_ATTEMPT_PERCENT_B = 0.8  # %B >= 0.8

    @property
    def name(self) -> str:
        return "bollinger"

    @property
    def min_data_length(self) -> int:
        return 60  # 60일 (백분위 계산용)

    def calculate_bollinger_bands(self, df: pd.DataFrame) -> pd.DataFrame:
        """볼린저 밴드 계산"""
        df = df.copy()

        # 중심선 (SMA)
        df["bb_middle"] = df["Close"].rolling(window=self.BB_PERIOD).mean()

        # 표준편차
        df["bb_std"] = df["Close"].rolling(window=self.BB_PERIOD).std()

        # 상단/하단 밴드
        df["bb_upper"] = df["bb_middle"] + (self.BB_STD * df["bb_std"])
        df["bb_lower"] = df["bb_middle"] - (self.BB_STD * df["bb_std"])

        # 밴드폭 (BandWidth)
        df["bandwidth"] = ((df["bb_upper"] - df["bb_lower"]) / df["bb_middle"]) * 100

        # %B 지표
        df["percent_b"] = (df["Close"] - df["bb_lower"]) / (df["bb_upper"] - df["bb_lower"])

        # 거래량 이동평균
        df["volume_ma"] = df["Volume"].rolling(window=self.BB_PERIOD).mean()

        # 거래량 비율
        df["volume_ratio"] = df["Volume"] / df["volume_ma"]

        return df

    def analyze(
        self,
        df: pd.DataFrame,
        ticker: str,
        name: str = "",
        market: str = "US"
    ) -> Optional[BollingerSignal]:
        """
        볼린저 밴드 스퀴즈 분석

        신호 조건:
        - 스퀴즈 (BandWidth 하위 20%): +25점
        - 강한 스퀴즈 (하위 10%): +35점 (대신)
        - 거래량 2배 이상 급증: +20점
        - 거래량 3배 이상: +30점 (대신)
        - 밴드 상단 돌파 시도 (%B >= 0.8): +15점

        최대 점수: 80점
        """
        try:
            if not self.has_sufficient_data(df):
                return None

            # 볼린저 밴드 계산
            df = self.calculate_bollinger_bands(df)

            # 현재 데이터
            current = df.iloc[-1]

            # NaN 체크
            if pd.isna(current["bb_middle"]) or pd.isna(current["bandwidth"]):
                return None

            # BandWidth 백분위 계산 (최근 60일 기준)
            recent_bandwidths = df["bandwidth"].tail(60).dropna()
            if len(recent_bandwidths) < 30:
                return None

            current_bandwidth = current["bandwidth"]
            bandwidth_percentile = (recent_bandwidths < current_bandwidth).sum() / len(recent_bandwidths) * 100

            # 스퀴즈 상태 판단
            is_strong_squeeze = bandwidth_percentile <= self.STRONG_SQUEEZE_PERCENTILE
            is_squeeze = bandwidth_percentile <= self.SQUEEZE_PERCENTILE

            # 거래량 상태 판단
            volume_ratio = current["volume_ratio"] if not pd.isna(current["volume_ratio"]) else 0
            strong_volume_surge = volume_ratio >= self.STRONG_VOLUME_SURGE_RATIO
            volume_surge = volume_ratio >= self.VOLUME_SURGE_RATIO

            # 돌파 시도 판단
            percent_b = current["percent_b"] if not pd.isna(current["percent_b"]) else 0.5
            band_breakout_attempt = percent_b >= self.BREAKOUT_ATTEMPT_PERCENT_B

            # 점수 계산
            score = self._calculate_score(
                is_squeeze=is_squeeze,
                is_strong_squeeze=is_strong_squeeze,
                volume_surge=volume_surge,
                strong_volume_surge=strong_volume_surge,
                band_breakout_attempt=band_breakout_attempt
            )

            return BollingerSignal(
                upper_band=round(current["bb_upper"], 2),
                middle_band=round(current["bb_middle"], 2),
                lower_band=round(current["bb_lower"], 2),
                bandwidth=round(current_bandwidth, 4),
                percent_b=round(percent_b, 4),
                is_squeeze=is_squeeze,
                is_strong_squeeze=is_strong_squeeze,
                bandwidth_percentile=round(bandwidth_percentile, 2),
                volume_ratio=round(volume_ratio, 2),
                volume_surge=volume_surge,
                strong_volume_surge=strong_volume_surge,
                band_breakout_attempt=band_breakout_attempt,
                score=score,
            )

        except Exception as e:
            logger.debug(f"볼린저 분석 실패 {ticker}: {e}")
            return None

    def _calculate_score(
        self,
        is_squeeze: bool,
        is_strong_squeeze: bool,
        volume_surge: bool,
        strong_volume_surge: bool,
        band_breakout_attempt: bool
    ) -> int:
        """
        점수 계산 (최대 80점)

        - 스퀴즈: +25점 / 강한 스퀴즈: +35점
        - 거래량 급증: +20점 / 강한 급증: +30점
        - 돌파 시도: +15점
        """
        score = 0

        # 스퀴즈 점수 (중복 불가)
        if is_strong_squeeze:
            score += 35
        elif is_squeeze:
            score += 25

        # 거래량 점수 (중복 불가)
        if strong_volume_surge:
            score += 30
        elif volume_surge:
            score += 20

        # 돌파 시도 점수
        if band_breakout_attempt:
            score += 15

        return min(score, 80)


def get_bollinger_analyzer() -> BollingerAnalyzer:
    """BollingerAnalyzer 인스턴스 생성"""
    return BollingerAnalyzer()
