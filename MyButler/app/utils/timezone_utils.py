# -*- coding: utf-8 -*-
"""
Timezone Utils
시간대 처리 유틸리티
"""
import logging
from datetime import datetime, date, timedelta
from typing import Tuple

import pytz

logger = logging.getLogger(__name__)

# 시간대 정의
KST = pytz.timezone("Asia/Seoul")
ET = pytz.timezone("US/Eastern")
UTC = pytz.UTC


def get_current_kst() -> datetime:
    """현재 한국 시간 반환"""
    return datetime.now(KST)


def get_current_et() -> datetime:
    """현재 미국 동부 시간 반환"""
    return datetime.now(ET)


def kst_to_et(kst_dt: datetime) -> datetime:
    """한국시간을 미국 동부시간으로 변환"""
    if kst_dt.tzinfo is None:
        kst_dt = KST.localize(kst_dt)
    return kst_dt.astimezone(ET)


def et_to_kst(et_dt: datetime) -> datetime:
    """미국 동부시간을 한국시간으로 변환"""
    if et_dt.tzinfo is None:
        et_dt = ET.localize(et_dt)
    return et_dt.astimezone(KST)


def is_dst_in_us(dt: datetime = None) -> bool:
    """미국 DST(서머타임) 여부 확인"""
    if dt is None:
        dt = datetime.now(ET)
    elif dt.tzinfo is None:
        dt = ET.localize(dt)
    else:
        dt = dt.astimezone(ET)

    return bool(dt.dst())


def get_us_market_close_kst(target_date: date = None) -> datetime:
    """
    미국 시장 마감 시간을 KST로 반환

    미국 시장 마감: ET 16:00
    - DST 기간: KST 05:00 (다음날)
    - 표준시 기간: KST 06:00 (다음날)
    """
    if target_date is None:
        target_date = get_current_et().date()

    # 미국 동부시간 16:00
    market_close_et = ET.localize(datetime.combine(target_date, datetime.min.time()).replace(hour=16))

    # KST로 변환 (다음날이 됨)
    market_close_kst = market_close_et.astimezone(KST)

    return market_close_kst


def get_recording_schedule_time() -> Tuple[int, int]:
    """
    기록 스케줄 시간 반환 (hour, minute)

    DST 여부에 따라 동적으로 변경:
    - DST 기간: 05:00 KST
    - 표준시 기간: 06:00 KST
    """
    if is_dst_in_us():
        return (5, 0)
    else:
        return (6, 0)


def get_trading_date_for_recording() -> date:
    """
    기록할 거래일 반환

    KST 기준으로 전일 미국 거래일을 반환
    예: KST 06:00에 실행 시, 전일 미국 거래일 반환
    """
    kst_now = get_current_kst()
    et_now = kst_to_et(kst_now)

    # 미국 동부시간 기준 현재 날짜
    # 시장 마감(16:00) 이후이면 해당일, 아니면 전일
    if et_now.hour >= 16:
        return et_now.date()
    else:
        return et_now.date() - timedelta(days=1)


def format_date_for_db(d: date) -> str:
    """DB 저장용 날짜 포맷 (YYYY-MM-DD)"""
    return d.strftime("%Y-%m-%d")


def parse_date_from_db(date_str: str) -> date:
    """DB에서 읽은 날짜 문자열 파싱"""
    return datetime.strptime(date_str, "%Y-%m-%d").date()
