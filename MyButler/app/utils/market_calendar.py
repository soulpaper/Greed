# -*- coding: utf-8 -*-
"""
Market Calendar
미국/일본/한국 휴장일 처리
"""
import logging
from datetime import date, timedelta
from typing import List

import holidays

logger = logging.getLogger(__name__)

# 미국 주식 시장 휴장일 (NYSE/NASDAQ)
US_MARKET_HOLIDAYS = holidays.NYSE()

# 일본 주식 시장 휴장일
JP_MARKET_HOLIDAYS = holidays.Japan()

# 한국 주식 시장 휴장일 (KRX)
KR_MARKET_HOLIDAYS = holidays.KRX()


def is_us_market_holiday(target_date: date) -> bool:
    """미국 시장 휴장일 여부 확인"""
    return target_date in US_MARKET_HOLIDAYS


def is_jp_market_holiday(target_date: date) -> bool:
    """일본 시장 휴장일 여부 확인"""
    return target_date in JP_MARKET_HOLIDAYS


def is_kr_market_holiday(target_date: date) -> bool:
    """한국 시장 휴장일 여부 확인"""
    return target_date in KR_MARKET_HOLIDAYS


def is_weekend(target_date: date) -> bool:
    """주말 여부 확인"""
    return target_date.weekday() >= 5


def is_us_trading_day(target_date: date) -> bool:
    """미국 거래일 여부 확인"""
    if is_weekend(target_date):
        return False
    if is_us_market_holiday(target_date):
        return False
    return True


def is_jp_trading_day(target_date: date) -> bool:
    """일본 거래일 여부 확인"""
    if is_weekend(target_date):
        return False
    if is_jp_market_holiday(target_date):
        return False
    return True


def is_kr_trading_day(target_date: date) -> bool:
    """한국 거래일 여부 확인"""
    if is_weekend(target_date):
        return False
    if is_kr_market_holiday(target_date):
        return False
    return True


def should_record_today(target_date: date = None, market: str = "US") -> bool:
    """
    오늘 기록 작업을 수행해야 하는지 확인

    Args:
        target_date: 확인할 날짜 (기본값: 오늘)
        market: 시장 코드 (US, JP, KR)

    Returns:
        거래일 여부
    """
    if target_date is None:
        target_date = date.today()

    if market == "KR":
        return is_kr_trading_day(target_date)
    elif market == "JP":
        return is_jp_trading_day(target_date)
    else:
        return is_us_trading_day(target_date)


def _get_trading_day_checker(market: str):
    """시장별 거래일 확인 함수 반환"""
    if market == "KR":
        return is_kr_trading_day
    elif market == "JP":
        return is_jp_trading_day
    else:
        return is_us_trading_day


def get_previous_trading_day(target_date: date, market: str = "US") -> date:
    """이전 거래일 반환"""
    check_func = _get_trading_day_checker(market)

    prev_date = target_date - timedelta(days=1)
    while not check_func(prev_date):
        prev_date -= timedelta(days=1)

    return prev_date


def get_next_trading_day(target_date: date, market: str = "US") -> date:
    """다음 거래일 반환"""
    check_func = _get_trading_day_checker(market)

    next_date = target_date + timedelta(days=1)
    while not check_func(next_date):
        next_date += timedelta(days=1)

    return next_date


def get_trading_days_in_range(start_date: date, end_date: date, market: str = "US") -> List[date]:
    """기간 내 거래일 목록 반환"""
    check_func = _get_trading_day_checker(market)

    trading_days = []
    current = start_date

    while current <= end_date:
        if check_func(current):
            trading_days.append(current)
        current += timedelta(days=1)

    return trading_days


def get_holiday_name(target_date: date, market: str = "US") -> str:
    """휴장일 이름 반환"""
    if market == "KR":
        return KR_MARKET_HOLIDAYS.get(target_date, "")
    elif market == "JP":
        return JP_MARKET_HOLIDAYS.get(target_date, "")
    else:
        return US_MARKET_HOLIDAYS.get(target_date, "")
