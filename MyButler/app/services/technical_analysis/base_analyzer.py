# -*- coding: utf-8 -*-
"""
Base Analyzer
기본 분석기 인터페이스
"""
from abc import ABC, abstractmethod
from typing import Optional, Any

import pandas as pd


class BaseAnalyzer(ABC):
    """기본 분석기 추상 클래스"""

    @property
    @abstractmethod
    def name(self) -> str:
        """분석기 이름"""
        pass

    @property
    @abstractmethod
    def min_data_length(self) -> int:
        """최소 필요 데이터 길이 (일 수)"""
        pass

    @abstractmethod
    def analyze(self, df: pd.DataFrame, ticker: str, name: str = "", market: str = "US") -> Optional[Any]:
        """
        데이터 분석 수행

        Args:
            df: OHLCV DataFrame (Open, High, Low, Close, Volume, Value)
            ticker: 종목 코드
            name: 종목명
            market: 시장 (US, KR)

        Returns:
            분석 결과 신호 객체 또는 None
        """
        pass

    def has_sufficient_data(self, df: pd.DataFrame) -> bool:
        """데이터 길이가 충분한지 확인"""
        return df is not None and len(df) >= self.min_data_length
