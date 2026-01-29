# -*- coding: utf-8 -*-
"""
History Controller
히스토리 조회 API 엔드포인트
"""
import logging
from datetime import date
from typing import Optional, List

from fastapi import APIRouter, HTTPException, Query, Depends, BackgroundTasks

from app.models.history_models import (
    StockHistoryResponse,
    SummaryHistoryResponse,
    DateCompareResponse,
    LatestRecordResponse,
    RecordingStatusResponse,
    ManualRecordRequest,
    ManualRecordResponse,
)
from app.services.history_service import get_history_service, HistoryService
from app.services.recording_service import get_recording_service, RecordingService
from app.scheduler.scheduler_manager import get_scheduler_manager

logger = logging.getLogger(__name__)

router = APIRouter(
    prefix="/api/v1/history",
    tags=["history"],
    responses={404: {"description": "Not found"}}
)


@router.get("/stocks", response_model=StockHistoryResponse)
async def get_stock_history(
    start_date: Optional[date] = Query(None, description="시작 날짜"),
    end_date: Optional[date] = Query(None, description="종료 날짜"),
    exchange: Optional[str] = Query(None, description="거래소 코드 (NASD, NYSE, AMEX, TKSE)"),
    ticker: Optional[str] = Query(None, description="종목 코드"),
    limit: int = Query(100, le=1000, description="조회 개수"),
    offset: int = Query(0, ge=0, description="시작 위치"),
    service: HistoryService = Depends(get_history_service)
):
    """
    종목별 히스토리 조회

    일일 기록된 종목 데이터를 조회합니다.
    """
    try:
        records, total_count = await service.get_stock_records(
            start_date=start_date,
            end_date=end_date,
            exchange=exchange,
            ticker=ticker,
            limit=limit,
            offset=offset
        )

        return StockHistoryResponse(
            records=records,
            total_count=total_count,
            limit=limit,
            offset=offset
        )
    except Exception as e:
        logger.error(f"종목 히스토리 조회 실패: {str(e)}")
        raise HTTPException(status_code=500, detail=f"조회 중 오류 발생: {str(e)}")


@router.get("/stocks/{ticker}")
async def get_ticker_history(
    ticker: str,
    start_date: Optional[date] = Query(None, description="시작 날짜"),
    end_date: Optional[date] = Query(None, description="종료 날짜"),
    limit: int = Query(100, le=1000, description="조회 개수"),
    service: HistoryService = Depends(get_history_service)
):
    """
    특정 종목 히스토리 조회

    특정 종목의 일일 기록 데이터를 조회합니다.
    """
    try:
        records = await service.get_stock_by_ticker(
            ticker=ticker,
            start_date=start_date,
            end_date=end_date,
            limit=limit
        )

        return {
            "ticker": ticker,
            "records": records,
            "count": len(records)
        }
    except Exception as e:
        logger.error(f"종목 {ticker} 히스토리 조회 실패: {str(e)}")
        raise HTTPException(status_code=500, detail=f"조회 중 오류 발생: {str(e)}")


@router.get("/summaries", response_model=SummaryHistoryResponse)
async def get_summary_history(
    start_date: Optional[date] = Query(None, description="시작 날짜"),
    end_date: Optional[date] = Query(None, description="종료 날짜"),
    exchange: Optional[str] = Query(None, description="거래소 코드"),
    limit: int = Query(100, le=1000, description="조회 개수"),
    offset: int = Query(0, ge=0, description="시작 위치"),
    service: HistoryService = Depends(get_history_service)
):
    """
    계좌 요약 히스토리 조회

    일일 기록된 계좌 요약 데이터를 조회합니다.
    """
    try:
        records, total_count = await service.get_summary_records(
            start_date=start_date,
            end_date=end_date,
            exchange=exchange,
            limit=limit,
            offset=offset
        )

        return SummaryHistoryResponse(
            records=records,
            total_count=total_count,
            limit=limit,
            offset=offset
        )
    except Exception as e:
        logger.error(f"요약 히스토리 조회 실패: {str(e)}")
        raise HTTPException(status_code=500, detail=f"조회 중 오류 발생: {str(e)}")


@router.get("/compare")
async def compare_dates(
    date1: date = Query(..., description="비교 기준 날짜"),
    date2: date = Query(..., description="비교 대상 날짜"),
    exchange: Optional[str] = Query(None, description="거래소 코드"),
    service: HistoryService = Depends(get_history_service)
):
    """
    날짜별 비교

    두 날짜의 종목 데이터를 비교합니다.
    """
    try:
        result = await service.compare_dates(
            date1=date1,
            date2=date2,
            exchange=exchange
        )

        return result
    except Exception as e:
        logger.error(f"날짜 비교 실패: {str(e)}")
        raise HTTPException(status_code=500, detail=f"비교 중 오류 발생: {str(e)}")


@router.get("/latest")
async def get_latest_records(
    service: HistoryService = Depends(get_history_service)
):
    """
    최근 기록 조회

    가장 최근 기록된 데이터를 조회합니다.
    """
    try:
        result = await service.get_latest_records()

        return result
    except Exception as e:
        logger.error(f"최근 기록 조회 실패: {str(e)}")
        raise HTTPException(status_code=500, detail=f"조회 중 오류 발생: {str(e)}")


@router.post("/record/manual", response_model=ManualRecordResponse)
async def trigger_manual_recording(
    request: ManualRecordRequest = None,
    background_tasks: BackgroundTasks = None,
    service: RecordingService = Depends(get_recording_service)
):
    """
    수동 기록 트리거

    수동으로 기록 작업을 실행합니다.
    """
    try:
        # 기본값 처리
        if request is None:
            request = ManualRecordRequest()

        # 즉시 실행 (백그라운드에서)
        result = await service.record_all_exchanges(
            record_date=request.target_date,
            target_exchanges=request.exchanges
        )

        if result.get("skipped"):
            return ManualRecordResponse(
                success=True,
                message=result.get("message", "기록이 스킵되었습니다."),
                record_date=result.get("record_date"),
                stocks_recorded=0,
                exchanges_processed=[]
            )

        return ManualRecordResponse(
            success=result.get("success", False),
            message=f"기록 완료: {result.get('status', 'UNKNOWN')}",
            record_date=result.get("record_date"),
            stocks_recorded=result.get("total_stocks", 0),
            exchanges_processed=result.get("exchanges_processed", [])
        )
    except Exception as e:
        logger.error(f"수동 기록 실패: {str(e)}")
        raise HTTPException(status_code=500, detail=f"기록 중 오류 발생: {str(e)}")


@router.get("/recording/status")
async def get_recording_status(
    service: RecordingService = Depends(get_recording_service)
):
    """
    기록 작업 상태 조회

    현재 기록 작업 상태와 스케줄러 상태를 조회합니다.
    """
    try:
        # 기록 서비스 상태
        recording_status = await service.get_recording_status()

        # 스케줄러 상태
        scheduler_manager = get_scheduler_manager()
        scheduler_status = scheduler_manager.get_status()

        return {
            "recording": recording_status,
            "scheduler": scheduler_status
        }
    except Exception as e:
        logger.error(f"기록 상태 조회 실패: {str(e)}")
        raise HTTPException(status_code=500, detail=f"상태 조회 중 오류 발생: {str(e)}")


@router.get("/recording/logs")
async def get_recording_logs(
    limit: int = Query(10, le=100, description="조회 개수"),
    service: HistoryService = Depends(get_history_service)
):
    """
    기록 로그 조회

    최근 기록 작업 로그를 조회합니다.
    """
    try:
        logs = await service.get_recording_logs(limit=limit)

        return {
            "logs": logs,
            "count": len(logs)
        }
    except Exception as e:
        logger.error(f"기록 로그 조회 실패: {str(e)}")
        raise HTTPException(status_code=500, detail=f"로그 조회 중 오류 발생: {str(e)}")
