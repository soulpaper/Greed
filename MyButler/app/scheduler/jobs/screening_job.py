# -*- coding: utf-8 -*-
"""
Screening Job
일일 스크리닝 작업
"""
import asyncio
import logging
from datetime import datetime, date

from app.services.screening_service import get_screening_service
from app.models.screening_models import MarketType

logger = logging.getLogger(__name__)


def run_daily_screening():
    """
    일일 스크리닝 작업 실행 (동기)

    APScheduler용 동기 래퍼
    """
    logger.info(f"일일 스크리닝 작업 시작: {datetime.now()}")

    try:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)

        try:
            result = loop.run_until_complete(run_daily_screening_async())
            return result
        finally:
            loop.close()

    except Exception as e:
        logger.error(f"일일 스크리닝 작업 중 오류 발생: {str(e)}", exc_info=True)
        return {"success": False, "error": str(e)}


async def run_daily_screening_async():
    """
    일일 스크리닝 작업 실행 (비동기)
    """
    logger.info(f"일일 스크리닝 작업 시작 (async): {datetime.now()}")

    try:
        service = get_screening_service()

        # 전체 시장 스크리닝
        result = service.run_screening(
            market=MarketType.ALL,
            min_score=20,  # 약한 매수 신호까지 포함
            perfect_only=False,
            limit=50
        )

        # 결과 집계 - StockSignal 그대로 사용 (필터별 점수 포함)
        all_signals = result.strong_buy + result.buy + result.weak_buy

        # DB 저장 (필터별 점수 포함)
        saved_count = await service.save_screening_results(all_signals)

        logger.info(f"일일 스크리닝 완료: {len(all_signals)}개 신호, {saved_count}개 저장")

        return {
            "success": True,
            "screening_date": result.screening_date.isoformat(),
            "total_signals": len(all_signals),
            "saved_count": saved_count,
            "summary": result.summary
        }

    except Exception as e:
        logger.error(f"일일 스크리닝 작업 중 오류 발생: {str(e)}", exc_info=True)
        return {"success": False, "error": str(e)}


async def run_manual_screening_async(
    market: str = "ALL",
    min_score: int = 50,
    perfect_only: bool = False,
    save_results: bool = True
):
    """
    수동 스크리닝 실행 (비동기)

    Args:
        market: 대상 시장 (US, KR, ALL)
        min_score: 최소 점수
        perfect_only: 완벽 조건만
        save_results: 결과 저장 여부
    """
    logger.info(f"수동 스크리닝 시작: market={market}, min_score={min_score}")

    try:
        service = get_screening_service()

        # 스크리닝 실행
        market_type = MarketType(market) if market else MarketType.ALL
        result = service.run_screening(
            market=market_type,
            min_score=min_score,
            perfect_only=perfect_only,
            limit=50
        )

        # 결과 저장 (필터별 점수 포함)
        saved_count = 0
        if save_results:
            all_signals = result.strong_buy + result.buy + result.weak_buy
            saved_count = await service.save_screening_results(all_signals)

        logger.info(f"수동 스크리닝 완료: {result.total_signals}개 신호")

        return {
            "success": True,
            "result": result,
            "saved_count": saved_count
        }

    except Exception as e:
        logger.error(f"수동 스크리닝 중 오류 발생: {str(e)}", exc_info=True)
        return {"success": False, "error": str(e)}
