# -*- coding: utf-8 -*-
"""
Recording Job
일일 기록 작업
"""
import asyncio
import logging
from datetime import datetime

from app.services.recording_service import get_recording_service
from app.config.scheduler_config import get_scheduler_config

logger = logging.getLogger(__name__)


def run_daily_recording():
    """
    일일 기록 작업 실행

    APScheduler는 동기 함수를 기대하므로,
    비동기 함수를 동기적으로 실행하는 래퍼
    """
    logger.info(f"일일 기록 작업 시작: {datetime.now()}")

    try:
        # 새 이벤트 루프에서 비동기 함수 실행
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)

        try:
            recording_service = get_recording_service()
            result = loop.run_until_complete(recording_service.record_all_exchanges())

            if result.get("skipped"):
                logger.info(f"일일 기록 스킵됨: {result.get('message')}")
            elif result.get("success"):
                logger.info(f"일일 기록 성공: {result.get('total_stocks')}개 종목")
            else:
                logger.error(f"일일 기록 실패: {result}")

            return result

        finally:
            loop.close()

    except Exception as e:
        logger.error(f"일일 기록 작업 중 오류 발생: {str(e)}", exc_info=True)
        return {"success": False, "error": str(e)}


async def run_daily_recording_async():
    """
    일일 기록 작업 비동기 실행

    FastAPI의 비동기 컨텍스트에서 직접 호출할 때 사용
    """
    logger.info(f"일일 기록 작업 시작 (async): {datetime.now()}")

    try:
        recording_service = get_recording_service()
        result = await recording_service.record_all_exchanges()

        if result.get("skipped"):
            logger.info(f"일일 기록 스킵됨: {result.get('message')}")
        elif result.get("success"):
            logger.info(f"일일 기록 성공: {result.get('total_stocks')}개 종목")
        else:
            logger.error(f"일일 기록 실패: {result}")

        return result

    except Exception as e:
        logger.error(f"일일 기록 작업 중 오류 발생: {str(e)}", exc_info=True)
        return {"success": False, "error": str(e)}


def run_manual_recording(target_date=None, exchanges=None):
    """
    수동 기록 작업 실행

    Args:
        target_date: 기록할 날짜 (None이면 자동 결정)
        exchanges: 기록할 거래소 목록 (None이면 모든 대상 거래소)
    """
    logger.info(f"수동 기록 작업 시작: date={target_date}, exchanges={exchanges}")

    try:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)

        try:
            recording_service = get_recording_service()
            result = loop.run_until_complete(
                recording_service.record_all_exchanges(
                    record_date=target_date,
                    target_exchanges=exchanges
                )
            )
            return result
        finally:
            loop.close()

    except Exception as e:
        logger.error(f"수동 기록 작업 중 오류 발생: {str(e)}", exc_info=True)
        return {"success": False, "error": str(e)}


async def run_manual_recording_async(target_date=None, exchanges=None):
    """
    수동 기록 작업 비동기 실행

    Args:
        target_date: 기록할 날짜 (None이면 자동 결정)
        exchanges: 기록할 거래소 목록 (None이면 모든 대상 거래소)
    """
    logger.info(f"수동 기록 작업 시작 (async): date={target_date}, exchanges={exchanges}")

    try:
        recording_service = get_recording_service()
        result = await recording_service.record_all_exchanges(
            record_date=target_date,
            target_exchanges=exchanges
        )
        return result

    except Exception as e:
        logger.error(f"수동 기록 작업 중 오류 발생: {str(e)}", exc_info=True)
        return {"success": False, "error": str(e)}
