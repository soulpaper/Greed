# -*- coding: utf-8 -*-
"""
Scheduler Config
APScheduler 설정
"""
import os
import logging
from functools import lru_cache
from typing import Dict, Any

import pytz

logger = logging.getLogger(__name__)


class SchedulerConfig:
    """스케줄러 설정"""

    def __init__(self):
        # 시간대 설정
        self.timezone = pytz.timezone("Asia/Seoul")
        self.us_eastern = pytz.timezone("US/Eastern")

        # ========== 해외주식 기록 설정 (미국 장 마감) ==========
        # DST 기간: 05:00 KST (미국 ET 16:00 = 장마감)
        # 표준시 기간: 06:00 KST (미국 ET 16:00 = 장마감)
        self.default_hour = 6
        self.default_minute = 0

        # 해외주식 작업 설정
        self.job_id = "daily_overseas_recording"
        self.job_name = "해외주식 일일 기록"

        # 대상 거래소 (미국 + 일본)
        self.target_exchanges = [
            ("NASD", "USD", "미국(나스닥)"),
            ("NYSE", "USD", "미국(뉴욕)"),
            ("AMEX", "USD", "미국(아멕스)"),
            ("TKSE", "JPY", "일본"),
        ]

        # ========== 국내주식 기록 설정 (한국 장 마감) ==========
        # 한국 장 마감: 15:30 KST → 정산 후 15:40에 기록
        self.domestic_hour = 15
        self.domestic_minute = 40

        # 국내주식 작업 설정
        self.domestic_job_id = "daily_domestic_recording"
        self.domestic_job_name = "국내주식 일일 기록"

        # 재시도 설정
        self.max_retries = 3
        self.retry_interval_minutes = 5

    def get_apscheduler_config(self) -> Dict[str, Any]:
        """APScheduler 설정 반환"""
        return {
            "apscheduler.jobstores.default": {
                "type": "memory"
            },
            "apscheduler.executors.default": {
                "class": "apscheduler.executors.pool:ThreadPoolExecutor",
                "max_workers": "5"
            },
            "apscheduler.job_defaults.coalesce": "true",
            "apscheduler.job_defaults.max_instances": "1",
            "apscheduler.timezone": str(self.timezone)
        }


@lru_cache()
def get_scheduler_config() -> SchedulerConfig:
    """스케줄러 설정 싱글톤"""
    return SchedulerConfig()
