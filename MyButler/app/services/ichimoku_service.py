# -*- coding: utf-8 -*-
"""
Ichimoku Service
일목균형표 계산 및 신호 분석 서비스
"""
import logging
from dataclasses import dataclass
from typing import Optional, Dict, Any, List
from enum import Enum

import pandas as pd
import numpy as np

logger = logging.getLogger(__name__)


class SignalStrength(Enum):
    """신호 강도"""
    STRONG_BUY = "STRONG_BUY"      # 강한 매수
    BUY = "BUY"                     # 매수
    WEAK_BUY = "WEAK_BUY"          # 약한 매수
    NEUTRAL = "NEUTRAL"             # 중립
    WEAK_SELL = "WEAK_SELL"        # 약한 매도
    SELL = "SELL"                   # 매도
    STRONG_SELL = "STRONG_SELL"    # 강한 매도


@dataclass
class IchimokuSignal:
    """일목균형표 신호 결과"""
    ticker: str
    name: str
    market: str
    current_price: float
    signal_strength: SignalStrength
    score: int  # -100 ~ 100

    # 개별 조건 충족 여부
    price_above_cloud: bool          # 주가 > 구름대
    tenkan_above_kijun: bool         # 전환선 > 기준선
    chikou_above_price: bool         # 후행스팬 > 26일전 주가
    cloud_bullish: bool              # 양운 (선행스팬A > 선행스팬B)

    # 추가 신호
    cloud_breakout: bool             # 구름대 돌파 (최근)
    golden_cross: bool               # 골든크로스 (최근)
    thin_cloud: bool                 # 얇은 구름 (변동 가능성)

    # 수치 데이터
    tenkan_sen: float                # 전환선
    kijun_sen: float                 # 기준선
    senkou_span_a: float             # 선행스팬A
    senkou_span_b: float             # 선행스팬B
    chikou_span: float               # 후행스팬

    # 거래대금
    avg_trading_value: float         # 5일 평균 거래대금

    def to_dict(self) -> Dict[str, Any]:
        return {
            "ticker": self.ticker,
            "name": self.name,
            "market": self.market,
            "current_price": self.current_price,
            "signal_strength": self.signal_strength.value,
            "score": self.score,
            "conditions": {
                "price_above_cloud": self.price_above_cloud,
                "tenkan_above_kijun": self.tenkan_above_kijun,
                "chikou_above_price": self.chikou_above_price,
                "cloud_bullish": self.cloud_bullish,
                "cloud_breakout": self.cloud_breakout,
                "golden_cross": self.golden_cross,
                "thin_cloud": self.thin_cloud,
            },
            "ichimoku_values": {
                "tenkan_sen": self.tenkan_sen,
                "kijun_sen": self.kijun_sen,
                "senkou_span_a": self.senkou_span_a,
                "senkou_span_b": self.senkou_span_b,
                "chikou_span": self.chikou_span,
            },
            "avg_trading_value": self.avg_trading_value,
        }


class IchimokuService:
    """일목균형표 서비스"""

    # 일목균형표 기본 기간
    TENKAN_PERIOD = 9    # 전환선
    KIJUN_PERIOD = 26    # 기준선
    SENKOU_B_PERIOD = 52 # 선행스팬B
    DISPLACEMENT = 26    # 선행/후행 이동

    def calculate_ichimoku(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        일목균형표 지표 계산

        Args:
            df: OHLCV DataFrame (Open, High, Low, Close, Volume)

        Returns:
            DataFrame with Ichimoku indicators
        """
        df = df.copy()

        # 전환선 (Tenkan-sen): 9일 (최고+최저)/2
        high_9 = df["High"].rolling(window=self.TENKAN_PERIOD).max()
        low_9 = df["Low"].rolling(window=self.TENKAN_PERIOD).min()
        df["tenkan_sen"] = (high_9 + low_9) / 2

        # 기준선 (Kijun-sen): 26일 (최고+최저)/2
        high_26 = df["High"].rolling(window=self.KIJUN_PERIOD).max()
        low_26 = df["Low"].rolling(window=self.KIJUN_PERIOD).min()
        df["kijun_sen"] = (high_26 + low_26) / 2

        # 선행스팬A (Senkou Span A): (전환선+기준선)/2, 26일 앞에 표시
        df["senkou_span_a"] = ((df["tenkan_sen"] + df["kijun_sen"]) / 2).shift(self.DISPLACEMENT)

        # 선행스팬B (Senkou Span B): 52일 (최고+최저)/2, 26일 앞에 표시
        high_52 = df["High"].rolling(window=self.SENKOU_B_PERIOD).max()
        low_52 = df["Low"].rolling(window=self.SENKOU_B_PERIOD).min()
        df["senkou_span_b"] = ((high_52 + low_52) / 2).shift(self.DISPLACEMENT)

        # 후행스팬 (Chikou Span): 현재 종가를 26일 뒤로
        df["chikou_span"] = df["Close"].shift(-self.DISPLACEMENT)

        # 구름대 상단/하단
        df["cloud_top"] = df[["senkou_span_a", "senkou_span_b"]].max(axis=1)
        df["cloud_bottom"] = df[["senkou_span_a", "senkou_span_b"]].min(axis=1)

        # 구름 두께
        df["cloud_thickness"] = abs(df["senkou_span_a"] - df["senkou_span_b"])

        return df

    def analyze_signal(
        self,
        df: pd.DataFrame,
        ticker: str,
        name: str = "",
        market: str = "US"
    ) -> Optional[IchimokuSignal]:
        """
        일목균형표 신호 분석

        Args:
            df: OHLCV DataFrame
            ticker: 종목 코드
            name: 종목명
            market: 시장 (US, KR)

        Returns:
            IchimokuSignal or None
        """
        try:
            # 일목균형표 계산
            df = self.calculate_ichimoku(df)

            # 최소 데이터 확인
            if len(df) < self.SENKOU_B_PERIOD + self.DISPLACEMENT + 5:
                return None

            # 현재 데이터 (가장 최근)
            current = df.iloc[-1]
            current_price = current["Close"]

            # 26일 전 데이터 (후행스팬 비교용)
            price_26_ago = df.iloc[-self.DISPLACEMENT - 1]["Close"] if len(df) > self.DISPLACEMENT else current_price

            # NaN 체크
            if pd.isna(current["tenkan_sen"]) or pd.isna(current["kijun_sen"]):
                return None
            if pd.isna(current["senkou_span_a"]) or pd.isna(current["senkou_span_b"]):
                return None

            # === 주요 조건 분석 ===

            # 1. 주가 > 구름대 (선행스팬A, 선행스팬B 모두 위)
            price_above_cloud = current_price > current["cloud_top"]

            # 2. 전환선 > 기준선
            tenkan_above_kijun = current["tenkan_sen"] > current["kijun_sen"]

            # 3. 후행스팬 > 26일 전 주가
            chikou_above_price = current_price > price_26_ago

            # 4. 양운 (선행스팬A > 선행스팬B)
            cloud_bullish = current["senkou_span_a"] > current["senkou_span_b"]

            # === 추가 신호 분석 ===

            # 구름대 돌파 감지 (최근 5일 내)
            cloud_breakout = self._detect_cloud_breakout(df, lookback=5)

            # 골든크로스 감지 (최근 5일 내)
            golden_cross = self._detect_golden_cross(df, lookback=5)

            # 얇은 구름 (변동 가능성 높음)
            avg_cloud_thickness = df["cloud_thickness"].tail(10).mean()
            current_thickness = current["cloud_thickness"]
            thin_cloud = current_thickness < avg_cloud_thickness * 0.5

            # === 점수 계산 ===
            score = self._calculate_score(
                price_above_cloud=price_above_cloud,
                tenkan_above_kijun=tenkan_above_kijun,
                chikou_above_price=chikou_above_price,
                cloud_bullish=cloud_bullish,
                cloud_breakout=cloud_breakout,
                golden_cross=golden_cross,
                current_price=current_price,
                cloud_top=current["cloud_top"],
                cloud_bottom=current["cloud_bottom"],
            )

            # === 신호 강도 결정 ===
            signal_strength = self._determine_signal_strength(score)

            # 평균 거래대금
            avg_trading_value = df["Value"].tail(5).mean() if "Value" in df.columns else 0

            return IchimokuSignal(
                ticker=ticker,
                name=name,
                market=market,
                current_price=round(current_price, 2),
                signal_strength=signal_strength,
                score=score,
                price_above_cloud=price_above_cloud,
                tenkan_above_kijun=tenkan_above_kijun,
                chikou_above_price=chikou_above_price,
                cloud_bullish=cloud_bullish,
                cloud_breakout=cloud_breakout,
                golden_cross=golden_cross,
                thin_cloud=thin_cloud,
                tenkan_sen=round(current["tenkan_sen"], 2),
                kijun_sen=round(current["kijun_sen"], 2),
                senkou_span_a=round(current["senkou_span_a"], 2),
                senkou_span_b=round(current["senkou_span_b"], 2),
                chikou_span=round(current_price, 2),  # 현재가 = 후행스팬 현재값
                avg_trading_value=round(avg_trading_value, 2),
            )

        except Exception as e:
            logger.debug(f"일목균형표 분석 실패 {ticker}: {e}")
            return None

    def _detect_cloud_breakout(self, df: pd.DataFrame, lookback: int = 5) -> bool:
        """구름대 돌파 감지"""
        if len(df) < lookback + 1:
            return False

        for i in range(1, lookback + 1):
            idx = -i
            prev_idx = -i - 1

            current = df.iloc[idx]
            previous = df.iloc[prev_idx]

            # 이전에는 구름 아래/안에 있다가 현재 구름 위로 돌파
            was_below_or_in = previous["Close"] <= previous["cloud_top"]
            now_above = current["Close"] > current["cloud_top"]

            if was_below_or_in and now_above:
                return True

        return False

    def _detect_golden_cross(self, df: pd.DataFrame, lookback: int = 5) -> bool:
        """골든크로스 감지 (전환선이 기준선 상향 돌파)"""
        if len(df) < lookback + 1:
            return False

        for i in range(1, lookback + 1):
            idx = -i
            prev_idx = -i - 1

            current = df.iloc[idx]
            previous = df.iloc[prev_idx]

            # 이전에는 전환선 < 기준선, 현재는 전환선 > 기준선
            was_below = previous["tenkan_sen"] <= previous["kijun_sen"]
            now_above = current["tenkan_sen"] > current["kijun_sen"]

            if was_below and now_above:
                return True

        return False

    def _calculate_score(
        self,
        price_above_cloud: bool,
        tenkan_above_kijun: bool,
        chikou_above_price: bool,
        cloud_bullish: bool,
        cloud_breakout: bool,
        golden_cross: bool,
        current_price: float,
        cloud_top: float,
        cloud_bottom: float,
    ) -> int:
        """
        매수 점수 계산 (-100 ~ 100)

        가중치:
        - 주가 > 구름대: 30점
        - 전환선 > 기준선: 20점
        - 후행스팬 > 26일전 주가: 20점
        - 양운: 10점
        - 구름대 돌파: 15점 (보너스)
        - 골든크로스: 10점 (보너스)
        """
        score = 0

        # 기본 조건 (최대 80점)
        if price_above_cloud:
            score += 30
        elif current_price > cloud_bottom:
            # 구름 안에 있음
            score += 10
        else:
            # 구름 아래
            score -= 20

        if tenkan_above_kijun:
            score += 20
        else:
            score -= 10

        if chikou_above_price:
            score += 20
        else:
            score -= 10

        if cloud_bullish:
            score += 10
        else:
            score -= 5

        # 보너스 신호
        if cloud_breakout:
            score += 15

        if golden_cross:
            score += 10

        # 범위 제한
        return max(-100, min(100, score))

    def _determine_signal_strength(self, score: int) -> SignalStrength:
        """점수에 따른 신호 강도 결정"""
        if score >= 80:
            return SignalStrength.STRONG_BUY
        elif score >= 50:
            return SignalStrength.BUY
        elif score >= 20:
            return SignalStrength.WEAK_BUY
        elif score >= -20:
            return SignalStrength.NEUTRAL
        elif score >= -50:
            return SignalStrength.WEAK_SELL
        elif score >= -80:
            return SignalStrength.SELL
        else:
            return SignalStrength.STRONG_SELL

    def get_buy_signals(
        self,
        signals: List[IchimokuSignal],
        min_score: int = 50
    ) -> List[IchimokuSignal]:
        """
        매수 신호만 필터링

        Args:
            signals: 분석된 신호 리스트
            min_score: 최소 점수 (기본 50)

        Returns:
            매수 신호 리스트 (점수 내림차순)
        """
        buy_signals = [s for s in signals if s.score >= min_score]
        return sorted(buy_signals, key=lambda x: x.score, reverse=True)

    def get_perfect_signals(self, signals: List[IchimokuSignal]) -> List[IchimokuSignal]:
        """
        완벽한 매수 신호 필터링
        (주가>구름 + 전환선>기준선 + 후행스팬>26일전주가)
        """
        perfect = [
            s for s in signals
            if s.price_above_cloud and s.tenkan_above_kijun and s.chikou_above_price
        ]
        return sorted(perfect, key=lambda x: x.score, reverse=True)


def get_ichimoku_service() -> IchimokuService:
    """IchimokuService 인스턴스 생성"""
    return IchimokuService()
