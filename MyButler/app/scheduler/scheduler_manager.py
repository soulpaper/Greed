# -*- coding: utf-8 -*-
"""
Scheduler Manager
APScheduler 관리
"""
import logging
from datetime import datetime
from typing import Optional, Dict, Any

from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.cron import CronTrigger

from app.config.scheduler_config import get_scheduler_config
from app.scheduler.jobs.recording_job import run_daily_recording, run_domestic_recording
from app.scheduler.jobs.screening_job import run_daily_screening
from app.utils.timezone_utils import get_recording_schedule_time, is_dst_in_us

logger = logging.getLogger(__name__)

# 스크리닝 작업 ID
SCREENING_JOB_ID = "daily_stock_screening"
SCREENING_JOB_NAME = "일일 주식 스크리닝"

# 국내주식 기록 작업 ID (config에서 관리)
# scheduler_config.domestic_job_id, domestic_job_name 사용


class SchedulerManager:
    """APScheduler 관리자"""

    _instance: Optional["SchedulerManager"] = None
    _scheduler: Optional[BackgroundScheduler] = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    def __init__(self):
        if self._scheduler is None:
            self.config = get_scheduler_config()
            self._scheduler = BackgroundScheduler(
                timezone=self.config.timezone,
                job_defaults={
                    "coalesce": True,
                    "max_instances": 1,
                    "misfire_grace_time": 3600  # 1시간 내 미스파이어 허용
                }
            )

    @property
    def scheduler(self) -> BackgroundScheduler:
        """스케줄러 인스턴스 반환"""
        return self._scheduler

    def start(self):
        """스케줄러 시작"""
        if not self._scheduler.running:
            self._add_recording_job()
            self._add_domestic_recording_job()
            self._add_screening_job()
            self._scheduler.start()
            logger.info("스케줄러 시작됨")
            self._log_next_run_times()

    def shutdown(self, wait: bool = True):
        """스케줄러 종료"""
        if self._scheduler.running:
            self._scheduler.shutdown(wait=wait)
            logger.info("스케줄러 종료됨")

    def _add_recording_job(self):
        """일일 기록 작업 추가"""
        hour, minute = get_recording_schedule_time()

        # 기존 작업 제거
        if self._scheduler.get_job(self.config.job_id):
            self._scheduler.remove_job(self.config.job_id)

        # CronTrigger로 평일에만 실행
        trigger = CronTrigger(
            day_of_week="mon-fri",
            hour=hour,
            minute=minute,
            timezone=self.config.timezone
        )

        self._scheduler.add_job(
            run_daily_recording,
            trigger=trigger,
            id=self.config.job_id,
            name=self.config.job_name,
            replace_existing=True
        )

        logger.info(f"해외주식 기록 작업 등록: 평일 {hour:02d}:{minute:02d} KST (DST={is_dst_in_us()})")

    def _add_domestic_recording_job(self):
        """국내주식 기록 작업 추가 (한국 장 마감 후)"""
        # 기존 작업 제거
        if self._scheduler.get_job(self.config.domestic_job_id):
            self._scheduler.remove_job(self.config.domestic_job_id)

        # CronTrigger로 평일 15:40에 실행 (한국 장 마감 15:30 후)
        trigger = CronTrigger(
            day_of_week="mon-fri",
            hour=self.config.domestic_hour,
            minute=self.config.domestic_minute,
            timezone=self.config.timezone
        )

        self._scheduler.add_job(
            run_domestic_recording,
            trigger=trigger,
            id=self.config.domestic_job_id,
            name=self.config.domestic_job_name,
            replace_existing=True
        )

        logger.info(f"국내주식 기록 작업 등록: 평일 {self.config.domestic_hour:02d}:{self.config.domestic_minute:02d} KST")

    def _add_screening_job(self):
        """일일 스크리닝 작업 추가 (매일 오전 8시 KST)"""
        # 기존 작업 제거
        if self._scheduler.get_job(SCREENING_JOB_ID):
            self._scheduler.remove_job(SCREENING_JOB_ID)

        # 평일 오전 8시에 실행 (한국 시장 장 시작 전)
        trigger = CronTrigger(
            day_of_week="mon-fri",
            hour=8,
            minute=0,
            timezone=self.config.timezone
        )

        self._scheduler.add_job(
            run_daily_screening,
            trigger=trigger,
            id=SCREENING_JOB_ID,
            name=SCREENING_JOB_NAME,
            replace_existing=True
        )

        logger.info(f"일일 스크리닝 작업 등록: 평일 08:00 KST")

    def _log_next_run_times(self):
        """다음 실행 시간 로깅"""
        recording_job = self._scheduler.get_job(self.config.job_id)
        if recording_job:
            logger.info(f"다음 해외주식 기록 작업 예정: {recording_job.next_run_time}")

        domestic_job = self._scheduler.get_job(self.config.domestic_job_id)
        if domestic_job:
            logger.info(f"다음 국내주식 기록 작업 예정: {domestic_job.next_run_time}")

        screening_job = self._scheduler.get_job(SCREENING_JOB_ID)
        if screening_job:
            logger.info(f"다음 스크리닝 작업 예정: {screening_job.next_run_time}")

    def _log_next_run_time(self):
        """다음 실행 시간 로깅 (하위 호환)"""
        self._log_next_run_times()

    def get_next_run_time(self) -> Optional[datetime]:
        """다음 실행 시간 반환"""
        job = self._scheduler.get_job(self.config.job_id)
        if job:
            return job.next_run_time
        return None

    def get_status(self) -> Dict[str, Any]:
        """스케줄러 상태 반환"""
        recording_job = self._scheduler.get_job(self.config.job_id)
        domestic_job = self._scheduler.get_job(self.config.domestic_job_id)
        screening_job = self._scheduler.get_job(SCREENING_JOB_ID)

        return {
            "running": self._scheduler.running,
            "is_dst": is_dst_in_us(),
            "jobs": {
                "overseas_recording": {
                    "job_id": self.config.job_id,
                    "job_name": self.config.job_name,
                    "next_run_time": recording_job.next_run_time if recording_job else None,
                    "scheduled_hour": get_recording_schedule_time()[0],
                    "scheduled_minute": get_recording_schedule_time()[1]
                },
                "domestic_recording": {
                    "job_id": self.config.domestic_job_id,
                    "job_name": self.config.domestic_job_name,
                    "next_run_time": domestic_job.next_run_time if domestic_job else None,
                    "scheduled_hour": self.config.domestic_hour,
                    "scheduled_minute": self.config.domestic_minute
                },
                "screening": {
                    "job_id": SCREENING_JOB_ID,
                    "job_name": SCREENING_JOB_NAME,
                    "next_run_time": screening_job.next_run_time if screening_job else None,
                    "scheduled_hour": 8,
                    "scheduled_minute": 0
                }
            }
        }

    def run_now(self):
        """즉시 실행"""
        logger.info("일일 기록 작업 즉시 실행 요청")
        self._scheduler.add_job(
            run_daily_recording,
            id=f"{self.config.job_id}_manual_{datetime.now().timestamp()}",
            name=f"{self.config.job_name} (수동)"
        )

    def update_schedule(self):
        """
        스케줄 업데이트

        DST 변경 시 호출하여 스케줄 시간 갱신
        """
        logger.info("스케줄 업데이트 시작")
        self._add_recording_job()
        self._add_domestic_recording_job()
        self._add_screening_job()
        self._log_next_run_times()

    def run_domestic_now(self):
        """국내주식 기록 즉시 실행"""
        logger.info("국내주식 기록 작업 즉시 실행 요청")
        self._scheduler.add_job(
            run_domestic_recording,
            id=f"{self.config.domestic_job_id}_manual_{datetime.now().timestamp()}",
            name=f"{self.config.domestic_job_name} (수동)"
        )

    def run_screening_now(self):
        """스크리닝 즉시 실행"""
        logger.info("스크리닝 작업 즉시 실행 요청")
        self._scheduler.add_job(
            run_daily_screening,
            id=f"{SCREENING_JOB_ID}_manual_{datetime.now().timestamp()}",
            name=f"{SCREENING_JOB_NAME} (수동)"
        )


# 싱글톤 인스턴스
_scheduler_manager: Optional[SchedulerManager] = None


def get_scheduler_manager() -> SchedulerManager:
    """스케줄러 관리자 싱글톤"""
    global _scheduler_manager
    if _scheduler_manager is None:
        _scheduler_manager = SchedulerManager()
    return _scheduler_manager
