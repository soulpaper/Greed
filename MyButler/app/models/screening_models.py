# -*- coding: utf-8 -*-
"""
Screening Models
주식 스크리닝 데이터 모델
"""
from datetime import date, datetime
from typing import List, Optional, Dict, Any
from decimal import Decimal
from enum import Enum

from pydantic import BaseModel, Field


class MarketType(str, Enum):
    """시장 유형"""
    US = "US"
    KR = "KR"
    ALL = "ALL"


class SignalType(str, Enum):
    """신호 유형"""
    STRONG_BUY = "STRONG_BUY"
    BUY = "BUY"
    WEAK_BUY = "WEAK_BUY"
    NEUTRAL = "NEUTRAL"
    WEAK_SELL = "WEAK_SELL"
    SELL = "SELL"
    STRONG_SELL = "STRONG_SELL"


class FilterType(str, Enum):
    """필터 유형"""
    ICHIMOKU = "ichimoku"
    BOLLINGER = "bollinger"
    MA_ALIGNMENT = "ma_alignment"
    CUP_HANDLE = "cup_handle"


class CombineMode(str, Enum):
    """필터 조합 모드"""
    ANY = "any"  # OR: 하나라도 충족
    ALL = "all"  # AND: 모두 충족


class ScreeningRequest(BaseModel):
    """스크리닝 요청"""
    market: MarketType = Field(default=MarketType.ALL, description="대상 시장")
    min_score: int = Field(default=50, ge=-100, le=100, description="최소 점수")
    perfect_only: bool = Field(default=False, description="완벽 조건만")
    limit: int = Field(default=20, le=100, description="결과 개수")
    filters: List[str] = Field(
        default=["ichimoku"],
        description="적용할 필터 목록: ichimoku, bollinger, ma_alignment, cup_handle"
    )
    combine_mode: CombineMode = Field(
        default=CombineMode.ANY,
        description="필터 조합 모드: any (OR) 또는 all (AND)"
    )


class StockSignal(BaseModel):
    """종목 신호"""
    ticker: str
    name: str
    market: str
    current_price: float
    signal_strength: str
    score: int

    # 일목균형표 조건 충족 여부
    price_above_cloud: bool = False
    tenkan_above_kijun: bool = False
    chikou_above_price: bool = False
    cloud_bullish: bool = False
    cloud_breakout: bool = False
    golden_cross: bool = False
    thin_cloud: bool = False

    # 일목균형표 수치
    tenkan_sen: float = 0.0
    kijun_sen: float = 0.0
    senkou_span_a: float = 0.0
    senkou_span_b: float = 0.0

    # 거래대금
    avg_trading_value: float = 0.0

    # 새 필터 신호 (볼린저 밴드)
    bollinger_squeeze: bool = False
    bollinger_score: int = 0
    bollinger_bandwidth: Optional[float] = None
    bollinger_percent_b: Optional[float] = None

    # 새 필터 신호 (이동평균 정배열)
    ma_perfect_alignment: bool = False
    ma_alignment_score: int = 0
    ma_disparity: Optional[float] = None

    # 새 필터 신호 (컵앤핸들)
    cup_handle_pattern: bool = False
    cup_handle_score: int = 0
    cup_handle_breakout_imminent: bool = False

    # 보너스 점수
    bonus_score: int = 0
    total_technical_score: int = 0
    active_patterns: List[str] = []

    class Config:
        from_attributes = True


class ScreeningResponse(BaseModel):
    """스크리닝 응답"""
    screening_date: date
    market: str
    total_scanned: int
    total_passed_filter: int
    total_signals: int

    # 신호 목록
    strong_buy: List[StockSignal] = []
    buy: List[StockSignal] = []
    weak_buy: List[StockSignal] = []

    # 요약
    summary: Dict[str, Any] = {}


class ScreeningResultCreate(BaseModel):
    """스크리닝 결과 생성 모델 (DB 저장용)"""
    screening_date: date
    ticker: str
    name: Optional[str] = None
    market: str
    current_price: float
    signal_strength: str
    score: int
    price_above_cloud: bool
    tenkan_above_kijun: bool
    chikou_above_price: bool
    cloud_bullish: bool
    cloud_breakout: bool
    golden_cross: bool
    avg_trading_value: float


class ScreeningResult(ScreeningResultCreate):
    """스크리닝 결과 조회 모델"""
    id: int
    created_at: datetime

    class Config:
        from_attributes = True


class ScreeningHistoryRequest(BaseModel):
    """스크리닝 히스토리 요청"""
    start_date: Optional[date] = None
    end_date: Optional[date] = None
    market: Optional[str] = None
    ticker: Optional[str] = None
    min_score: int = Field(default=50, description="최소 점수")
    limit: int = Field(default=100, le=500)
    offset: int = Field(default=0, ge=0)


class ScreeningHistoryResponse(BaseModel):
    """스크리닝 히스토리 응답"""
    records: List[ScreeningResult]
    total_count: int
    limit: int
    offset: int


class ScreeningStatusResponse(BaseModel):
    """스크리닝 상태 응답"""
    is_running: bool
    last_screening_date: Optional[date] = None
    last_screening_market: Optional[str] = None
    last_total_signals: int = 0
    next_scheduled: Optional[datetime] = None


class DailyRecommendation(BaseModel):
    """일일 추천 종목"""
    date: date
    us_recommendations: List[StockSignal]
    kr_recommendations: List[StockSignal]
    total_count: int
    generated_at: datetime
