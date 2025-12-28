from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.cron import CronTrigger
from daily_asset_tracker.service import fetch_and_save_account_status
import logging

logger = logging.getLogger(__name__)

scheduler = BackgroundScheduler()

def start_scheduler():
    # 매일 한국 시간 05:00에 실행
    trigger = CronTrigger(hour=5, minute=0, timezone='Asia/Seoul')

    scheduler.add_job(
        fetch_and_save_account_status,
        trigger=trigger,
        id='daily_account_check',
        name='Daily Account Status Check',
        replace_existing=True
    )

    scheduler.start()
    logger.info("Scheduler started. Job 'daily_account_check' scheduled for 05:00 KST.")

def shutdown_scheduler():
    scheduler.shutdown()
    logger.info("Scheduler shut down.")
