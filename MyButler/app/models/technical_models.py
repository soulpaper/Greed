# -*- coding: utf-8 -*-
"""
Technical Analysis Models
기술적 분석 데이터 모델
"""
from dataclasses import dataclass, field
from typing import Optional, List, Dict, Any
from enum import Enum


class PatternType(str, Enum):
    """패턴 유형"""
    BOLLINGER_SQUEEZE = "BOLLINGER_SQUEEZE"
    MA_ALIGNMENT = "MA_ALIGNMENT"
    CUP_HANDLE = "CUP_HANDLE"


@dataclass
class BollingerSignal:
    """볼린저 밴드 스퀴즈 신호"""
    # 지표 값
    upper_band: float
    middle_band: float
    lower_band: float
    bandwidth: float  # (Upper - Lower) / Middle × 100
    percent_b: float  # (Close - Lower) / (Upper - Lower)

    # 스퀴즈 상태
    is_squeeze: bool  # BandWidth 하위 20%
    is_strong_squeeze: bool  # BandWidth 하위 10%
    bandwidth_percentile: float  # 현재 BandWidth의 백분위

    # 거래량 상태
    volume_ratio: float  # 현재 거래량 / 20일 평균 거래량
    volume_surge: bool  # 2배 이상
    strong_volume_surge: bool  # 3배 이상

    # 밴드 상태
    band_breakout_attempt: bool  # %B >= 0.8 (상단 돌파 시도)

    # 점수
    score: int  # 최대 80점

    def to_dict(self) -> Dict[str, Any]:
        return {
            "upper_band": self.upper_band,
            "middle_band": self.middle_band,
            "lower_band": self.lower_band,
            "bandwidth": self.bandwidth,
            "percent_b": self.percent_b,
            "is_squeeze": self.is_squeeze,
            "is_strong_squeeze": self.is_strong_squeeze,
            "bandwidth_percentile": self.bandwidth_percentile,
            "volume_ratio": self.volume_ratio,
            "volume_surge": self.volume_surge,
            "strong_volume_surge": self.strong_volume_surge,
            "band_breakout_attempt": self.band_breakout_attempt,
            "score": self.score,
        }


@dataclass
class MAAlignmentSignal:
    """이동평균선 정배열 신호"""
    # 이동평균 값
    sma_5: float
    sma_20: float
    sma_60: float
    sma_120: float

    # 이격도
    disparity: float  # (Price - SMA_20) / SMA_20 × 100

    # 정배열 상태
    is_perfect_alignment: bool  # Price > 5 > 20 > 60 > 120
    is_partial_alignment: bool  # 3단계 정배열
    alignment_count: int  # 정배열 단계 수 (0-4)

    # 골든크로스 상태
    golden_cross_5_20: bool  # 단기 GC (5/20)
    golden_cross_20_60: bool  # 중기 GC (20/60)
    golden_cross_60_120: bool  # 장기 GC (60/120)

    # 이격도 상태
    disparity_optimal: bool  # 이격도 5~15%
    disparity_overheated: bool  # 이격도 > 15%

    # 점수
    score: int  # 최대 95점

    def to_dict(self) -> Dict[str, Any]:
        return {
            "sma_5": self.sma_5,
            "sma_20": self.sma_20,
            "sma_60": self.sma_60,
            "sma_120": self.sma_120,
            "disparity": self.disparity,
            "is_perfect_alignment": self.is_perfect_alignment,
            "is_partial_alignment": self.is_partial_alignment,
            "alignment_count": self.alignment_count,
            "golden_cross_5_20": self.golden_cross_5_20,
            "golden_cross_20_60": self.golden_cross_20_60,
            "golden_cross_60_120": self.golden_cross_60_120,
            "disparity_optimal": self.disparity_optimal,
            "disparity_overheated": self.disparity_overheated,
            "score": self.score,
        }


@dataclass
class CupHandleSignal:
    """컵 앤 핸들 패턴 신호"""
    # 컵 패턴 정보
    cup_detected: bool
    cup_start_date: Optional[str] = None
    cup_bottom_date: Optional[str] = None
    cup_end_date: Optional[str] = None
    cup_depth_percent: float = 0.0  # 좌측 고점 대비 하락률
    cup_duration_days: int = 0

    # 핸들 패턴 정보
    handle_detected: bool = False
    handle_depth_percent: float = 0.0  # 우측 고점 대비 하락률

    # 주요 가격 레벨
    left_peak_price: float = 0.0
    cup_bottom_price: float = 0.0
    right_peak_price: float = 0.0
    current_price: float = 0.0

    # 돌파 상태
    breakout_imminent: bool = False  # 전고점 -3% 이내
    breakout_confirmed: bool = False  # 전고점 상회

    # 거래량 상태
    volume_ratio: float = 0.0  # 현재 거래량 / 20일 평균
    volume_surge: bool = False  # 2배 이상

    # 점수
    score: int = 0  # 최대 100점

    def to_dict(self) -> Dict[str, Any]:
        return {
            "cup_detected": self.cup_detected,
            "cup_start_date": self.cup_start_date,
            "cup_bottom_date": self.cup_bottom_date,
            "cup_end_date": self.cup_end_date,
            "cup_depth_percent": self.cup_depth_percent,
            "cup_duration_days": self.cup_duration_days,
            "handle_detected": self.handle_detected,
            "handle_depth_percent": self.handle_depth_percent,
            "left_peak_price": self.left_peak_price,
            "cup_bottom_price": self.cup_bottom_price,
            "right_peak_price": self.right_peak_price,
            "current_price": self.current_price,
            "breakout_imminent": self.breakout_imminent,
            "breakout_confirmed": self.breakout_confirmed,
            "volume_ratio": self.volume_ratio,
            "volume_surge": self.volume_surge,
            "score": self.score,
        }


@dataclass
class TechnicalSignal:
    """통합 기술적 분석 신호"""
    ticker: str
    name: str
    market: str
    current_price: float

    # 개별 필터 신호
    bollinger: Optional[BollingerSignal] = None
    ma_alignment: Optional[MAAlignmentSignal] = None
    cup_handle: Optional[CupHandleSignal] = None

    # 통합 점수
    total_score: int = 0
    active_patterns: List[str] = field(default_factory=list)

    # 개별 점수
    bollinger_score: int = 0
    ma_alignment_score: int = 0
    cup_handle_score: int = 0

    # 보너스 점수
    bonus_score: int = 0

    def to_dict(self) -> Dict[str, Any]:
        return {
            "ticker": self.ticker,
            "name": self.name,
            "market": self.market,
            "current_price": self.current_price,
            "bollinger": self.bollinger.to_dict() if self.bollinger else None,
            "ma_alignment": self.ma_alignment.to_dict() if self.ma_alignment else None,
            "cup_handle": self.cup_handle.to_dict() if self.cup_handle else None,
            "total_score": self.total_score,
            "active_patterns": self.active_patterns,
            "bollinger_score": self.bollinger_score,
            "ma_alignment_score": self.ma_alignment_score,
            "cup_handle_score": self.cup_handle_score,
            "bonus_score": self.bonus_score,
        }
