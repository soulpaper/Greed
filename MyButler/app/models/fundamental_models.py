# -*- coding: utf-8 -*-
"""
Fundamental Analysis Models
펀더멘탈 분석 데이터 모델
"""
from dataclasses import dataclass, field
from typing import Optional, List, Dict, Any
from enum import Enum


class FundamentalPatternType(str, Enum):
    """펀더멘탈 패턴 유형"""
    ROE_EXCELLENCE = "ROE_EXCELLENCE"
    GPM_EXCELLENCE = "GPM_EXCELLENCE"
    LOW_DEBT = "LOW_DEBT"
    CAPITAL_EFFICIENT = "CAPITAL_EFFICIENT"


@dataclass
class ROESignal:
    """ROE (자기자본이익률) 분석 신호 - 최대 30점"""
    # 현재 ROE
    current_roe: float  # 현재 ROE (%)

    # 10년 데이터 통계
    roe_history: List[float] = field(default_factory=list)  # 연도별 ROE
    roe_mean: float = 0.0  # 평균 ROE
    roe_std: float = 0.0  # 표준편차
    years_available: int = 0  # 사용 가능한 연도 수

    # ROE 조건 충족 여부
    roe_above_20: bool = False  # ROE >= 20%
    roe_above_15: bool = False  # ROE >= 15%
    roe_above_10: bool = False  # ROE >= 10%

    # 일관성 (표준편차 기준)
    is_highly_consistent: bool = False  # 표준편차 <= 3%
    is_consistent: bool = False  # 표준편차 <= 5%

    # 추세
    trend_direction: str = "neutral"  # up, down, neutral
    trend_score: int = 0  # 추세 점수 (-5 ~ +5)

    # 점수
    score: int = 0  # 최대 30점

    def to_dict(self) -> Dict[str, Any]:
        return {
            "current_roe": self.current_roe,
            "roe_history": self.roe_history,
            "roe_mean": self.roe_mean,
            "roe_std": self.roe_std,
            "years_available": self.years_available,
            "roe_above_20": self.roe_above_20,
            "roe_above_15": self.roe_above_15,
            "roe_above_10": self.roe_above_10,
            "is_highly_consistent": self.is_highly_consistent,
            "is_consistent": self.is_consistent,
            "trend_direction": self.trend_direction,
            "trend_score": self.trend_score,
            "score": self.score,
        }


@dataclass
class GPMSignal:
    """GPM (매출총이익률) 분석 신호 - 최대 25점"""
    # 현재 GPM
    current_gpm: float  # 현재 GPM (%)

    # 3년 데이터
    gpm_history: List[float] = field(default_factory=list)  # 연도별 GPM
    years_available: int = 0

    # GPM 조건 충족 여부
    gpm_above_50: bool = False  # GPM >= 50%
    gpm_above_40: bool = False  # GPM >= 40%
    gpm_above_30: bool = False  # GPM >= 30%

    # 3년 연속 유지/상승
    three_year_stable_or_rising: bool = False

    # 점수
    score: int = 0  # 최대 25점

    def to_dict(self) -> Dict[str, Any]:
        return {
            "current_gpm": self.current_gpm,
            "gpm_history": self.gpm_history,
            "years_available": self.years_available,
            "gpm_above_50": self.gpm_above_50,
            "gpm_above_40": self.gpm_above_40,
            "gpm_above_30": self.gpm_above_30,
            "three_year_stable_or_rising": self.three_year_stable_or_rising,
            "score": self.score,
        }


@dataclass
class DebtSignal:
    """부채비율 분석 신호 - 최대 25점"""
    # 현재 부채비율
    current_debt_ratio: float  # 부채비율 (%) = 총부채 / 자기자본 * 100

    # 상환 능력
    total_debt: float = 0.0  # 총부채
    net_income: float = 0.0  # 순이익
    repayment_ratio: float = 0.0  # 순이익/부채 비율 (%)
    years_to_repay: float = 0.0  # 상환 예상 연수

    # 부채비율 조건 충족 여부
    debt_below_50: bool = False  # 부채비율 <= 50%
    debt_below_100: bool = False  # 부채비율 <= 100%
    debt_below_150: bool = False  # 부채비율 <= 150%
    debt_above_200: bool = False  # 부채비율 > 200% (감점)

    # 상환 능력
    can_repay_in_5_years: bool = False  # 5년 내 상환 가능
    can_repay_in_10_years: bool = False  # 10년 내 상환 가능

    # 점수
    score: int = 0  # 최대 25점

    def to_dict(self) -> Dict[str, Any]:
        return {
            "current_debt_ratio": self.current_debt_ratio,
            "total_debt": self.total_debt,
            "net_income": self.net_income,
            "repayment_ratio": self.repayment_ratio,
            "years_to_repay": self.years_to_repay,
            "debt_below_50": self.debt_below_50,
            "debt_below_100": self.debt_below_100,
            "debt_below_150": self.debt_below_150,
            "debt_above_200": self.debt_above_200,
            "can_repay_in_5_years": self.can_repay_in_5_years,
            "can_repay_in_10_years": self.can_repay_in_10_years,
            "score": self.score,
        }


@dataclass
class CapExSignal:
    """CapEx (자본적지출) 분석 신호 - 최대 20점"""
    # 현재 CapEx 비율
    current_capex: float = 0.0  # 현재 CapEx
    current_net_income: float = 0.0  # 현재 순이익
    capex_to_income_ratio: float = 0.0  # CapEx/순이익 비율 (%)

    # 3년 데이터
    capex_ratio_history: List[float] = field(default_factory=list)  # 연도별 CapEx/순이익 비율
    capex_ratio_3y_avg: float = 0.0  # 3년 평균 비율
    years_available: int = 0

    # CapEx 조건 충족 여부
    capex_below_15: bool = False  # CapEx/순이익 < 15%
    capex_below_25: bool = False  # CapEx/순이익 < 25%
    capex_below_35: bool = False  # CapEx/순이익 < 35%
    capex_above_50: bool = False  # CapEx/순이익 >= 50% (감점)

    # 안정성 (3년 평균 대비)
    is_stable: bool = False  # 현재 비율이 3년 평균의 20% 이내

    # 점수
    score: int = 0  # 최대 20점

    def to_dict(self) -> Dict[str, Any]:
        return {
            "current_capex": self.current_capex,
            "current_net_income": self.current_net_income,
            "capex_to_income_ratio": self.capex_to_income_ratio,
            "capex_ratio_history": self.capex_ratio_history,
            "capex_ratio_3y_avg": self.capex_ratio_3y_avg,
            "years_available": self.years_available,
            "capex_below_15": self.capex_below_15,
            "capex_below_25": self.capex_below_25,
            "capex_below_35": self.capex_below_35,
            "capex_above_50": self.capex_above_50,
            "is_stable": self.is_stable,
            "score": self.score,
        }


@dataclass
class FundamentalSignal:
    """통합 펀더멘탈 분석 신호"""
    ticker: str
    name: str
    market: str
    current_price: float

    # 개별 분석 신호
    roe: Optional[ROESignal] = None
    gpm: Optional[GPMSignal] = None
    debt: Optional[DebtSignal] = None
    capex: Optional[CapExSignal] = None

    # 통합 점수
    total_score: int = 0  # 최대 100점
    active_patterns: List[str] = field(default_factory=list)

    # 개별 점수
    roe_score: int = 0
    gpm_score: int = 0
    debt_score: int = 0
    capex_score: int = 0

    # 보너스 점수
    bonus_score: int = 0

    def to_dict(self) -> Dict[str, Any]:
        return {
            "ticker": self.ticker,
            "name": self.name,
            "market": self.market,
            "current_price": self.current_price,
            "roe": self.roe.to_dict() if self.roe else None,
            "gpm": self.gpm.to_dict() if self.gpm else None,
            "debt": self.debt.to_dict() if self.debt else None,
            "capex": self.capex.to_dict() if self.capex else None,
            "total_score": self.total_score,
            "active_patterns": self.active_patterns,
            "roe_score": self.roe_score,
            "gpm_score": self.gpm_score,
            "debt_score": self.debt_score,
            "capex_score": self.capex_score,
            "bonus_score": self.bonus_score,
        }


@dataclass
class FundamentalData:
    """재무 데이터 컨테이너"""
    ticker: str
    name: str = ""
    market: str = "US"

    # ROE 데이터 (연도별)
    roe_data: Dict[int, float] = field(default_factory=dict)  # {year: roe}

    # GPM 데이터 (연도별)
    gpm_data: Dict[int, float] = field(default_factory=dict)  # {year: gpm}

    # 부채 데이터
    total_debt: float = 0.0
    total_equity: float = 0.0
    net_income: float = 0.0

    # CapEx 데이터 (연도별)
    capex_data: Dict[int, float] = field(default_factory=dict)  # {year: capex}
    net_income_data: Dict[int, float] = field(default_factory=dict)  # {year: net_income}

    # 현재 가격
    current_price: float = 0.0

    # 데이터 유효성
    is_valid: bool = False
    error_message: str = ""
