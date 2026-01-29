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

        # 결과 집계
        all_signals = []

        # IchimokuSignal 객체로 변환하여 저장
        from app.services.ichimoku_service import IchimokuSignal, SignalStrength

        for stock_signal in result.strong_buy + result.buy + result.weak_buy:
            # StockSignal을 IchimokuSignal로 변환
            signal = IchimokuSignal(
                ticker=stock_signal.ticker,
                name=stock_signal.name,
                market=stock_signal.market,
                current_price=stock_signal.current_price,
                signal_strength=SignalStrength(stock_signal.signal_strength),
                score=stock_signal.score,
                price_above_cloud=stock_signal.price_above_cloud,
                tenkan_above_kijun=stock_signal.tenkan_above_kijun,
                chikou_above_price=stock_signal.chikou_above_price,
                cloud_bullish=stock_signal.cloud_bullish,
                cloud_breakout=stock_signal.cloud_breakout,
                golden_cross=stock_signal.golden_cross,
                thin_cloud=stock_signal.thin_cloud,
                tenkan_sen=stock_signal.tenkan_sen,
                kijun_sen=stock_signal.kijun_sen,
                senkou_span_a=stock_signal.senkou_span_a,
                senkou_span_b=stock_signal.senkou_span_b,
                chikou_span=stock_signal.current_price,
                avg_trading_value=stock_signal.avg_trading_value,
            )
            all_signals.append(signal)

        # DB 저장
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

        # 결과 저장
        saved_count = 0
        if save_results:
            from app.services.ichimoku_service import IchimokuSignal, SignalStrength

            all_signals = []
            for stock_signal in result.strong_buy + result.buy + result.weak_buy:
                signal = IchimokuSignal(
                    ticker=stock_signal.ticker,
                    name=stock_signal.name,
                    market=stock_signal.market,
                    current_price=stock_signal.current_price,
                    signal_strength=SignalStrength(stock_signal.signal_strength),
                    score=stock_signal.score,
                    price_above_cloud=stock_signal.price_above_cloud,
                    tenkan_above_kijun=stock_signal.tenkan_above_kijun,
                    chikou_above_price=stock_signal.chikou_above_price,
                    cloud_bullish=stock_signal.cloud_bullish,
                    cloud_breakout=stock_signal.cloud_breakout,
                    golden_cross=stock_signal.golden_cross,
                    thin_cloud=stock_signal.thin_cloud,
                    tenkan_sen=stock_signal.tenkan_sen,
                    kijun_sen=stock_signal.kijun_sen,
                    senkou_span_a=stock_signal.senkou_span_a,
                    senkou_span_b=stock_signal.senkou_span_b,
                    chikou_span=stock_signal.current_price,
                    avg_trading_value=stock_signal.avg_trading_value,
                )
                all_signals.append(signal)

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
