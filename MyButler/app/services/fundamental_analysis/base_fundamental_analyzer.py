# -*- coding: utf-8 -*-
"""
Base Fundamental Analyzer
펀더멘탈 분석기 기본 인터페이스
"""
from abc import ABC, abstractmethod
from typing import Optional, Any

from app.models.fundamental_models import FundamentalData


class BaseFundamentalAnalyzer(ABC):
    """펀더멘탈 분석기 추상 기본 클래스"""

    @property
    @abstractmethod
    def name(self) -> str:
        """분석기 이름"""
        pass

    @property
    @abstractmethod
    def max_score(self) -> int:
        """최대 점수"""
        pass

    @property
    @abstractmethod
    def min_years_required(self) -> int:
        """최소 필요 데이터 연수"""
        pass

    @abstractmethod
    def analyze(
        self,
        data: FundamentalData,
        ticker: str,
        name: str = "",
        market: str = "US"
    ) -> Optional[Any]:
        """
        펀더멘탈 데이터 분석 수행

        Args:
            data: FundamentalData 객체 (재무 데이터 포함)
            ticker: 종목 코드
            name: 종목명
            market: 시장 (US, KR)

        Returns:
            분석 결과 신호 객체 또는 None
        """
        pass

    def has_sufficient_data(self, data: FundamentalData) -> bool:
        """데이터가 충분한지 확인"""
        return data is not None and data.is_valid
