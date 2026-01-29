# -*- coding: utf-8 -*-
"""
History Models
기록용 데이터 모델
"""
from datetime import date, datetime
from typing import List, Optional
from decimal import Decimal

from pydantic import BaseModel, Field


class StockRecordCreate(BaseModel):
    """종목 기록 생성 모델"""
    record_date: date
    exchange: str
    currency: str
    ticker: str
    stock_name: Optional[str] = None
    quantity: Optional[Decimal] = None
    avg_purchase_price: Optional[Decimal] = None
    current_price: Optional[Decimal] = None
    purchase_amount: Optional[Decimal] = None
    eval_amount: Optional[Decimal] = None
    profit_loss_amount: Optional[Decimal] = None
    profit_loss_rate: Optional[Decimal] = None


class StockRecord(StockRecordCreate):
    """종목 기록 조회 모델"""
    id: int
    created_at: datetime

    class Config:
        from_attributes = True


class SummaryRecordCreate(BaseModel):
    """계좌 요약 기록 생성 모델"""
    record_date: date
    exchange: str
    currency: str
    total_purchase_amount: Optional[Decimal] = None
    total_eval_amount: Optional[Decimal] = None
    total_profit_loss: Optional[Decimal] = None
    total_profit_rate: Optional[Decimal] = None
    stock_count: Optional[int] = None


class SummaryRecord(SummaryRecordCreate):
    """계좌 요약 기록 조회 모델"""
    id: int
    created_at: datetime

    class Config:
        from_attributes = True


class RecordingLogCreate(BaseModel):
    """기록 로그 생성 모델"""
    record_date: date
    status: str = "STARTED"


class RecordingLog(BaseModel):
    """기록 로그 조회 모델"""
    id: int
    record_date: date
    started_at: datetime
    completed_at: Optional[datetime] = None
    status: str
    exchanges_processed: Optional[str] = None
    total_stocks: int = 0
    error_message: Optional[str] = None

    class Config:
        from_attributes = True


class StockHistoryRequest(BaseModel):
    """종목 히스토리 조회 요청"""
    start_date: Optional[date] = None
    end_date: Optional[date] = None
    exchange: Optional[str] = None
    ticker: Optional[str] = None
    limit: int = Field(default=100, le=1000)
    offset: int = Field(default=0, ge=0)


class StockHistoryResponse(BaseModel):
    """종목 히스토리 조회 응답"""
    records: List[StockRecord]
    total_count: int
    limit: int
    offset: int


class SummaryHistoryRequest(BaseModel):
    """계좌 요약 히스토리 조회 요청"""
    start_date: Optional[date] = None
    end_date: Optional[date] = None
    exchange: Optional[str] = None
    limit: int = Field(default=100, le=1000)
    offset: int = Field(default=0, ge=0)


class SummaryHistoryResponse(BaseModel):
    """계좌 요약 히스토리 조회 응답"""
    records: List[SummaryRecord]
    total_count: int
    limit: int
    offset: int


class DateCompareRequest(BaseModel):
    """날짜별 비교 요청"""
    date1: date
    date2: date
    exchange: Optional[str] = None


class StockComparison(BaseModel):
    """종목 비교 결과"""
    ticker: str
    stock_name: Optional[str] = None
    exchange: str
    date1_price: Optional[Decimal] = None
    date2_price: Optional[Decimal] = None
    price_change: Optional[Decimal] = None
    price_change_rate: Optional[Decimal] = None
    date1_quantity: Optional[Decimal] = None
    date2_quantity: Optional[Decimal] = None
    quantity_change: Optional[Decimal] = None


class DateCompareResponse(BaseModel):
    """날짜별 비교 응답"""
    date1: date
    date2: date
    comparisons: List[StockComparison]
    summary: dict


class LatestRecordResponse(BaseModel):
    """최근 기록 응답"""
    record_date: date
    exchanges: dict
    total_stocks: int


class RecordingStatusResponse(BaseModel):
    """기록 작업 상태 응답"""
    status: str
    last_record_date: Optional[date] = None
    last_status: Optional[str] = None
    next_scheduled: Optional[datetime] = None
    is_running: bool = False


class ManualRecordRequest(BaseModel):
    """수동 기록 요청"""
    target_date: Optional[date] = None
    exchanges: Optional[List[str]] = None


class ManualRecordResponse(BaseModel):
    """수동 기록 응답"""
    success: bool
    message: str
    record_date: Optional[date] = None
    stocks_recorded: int = 0
    exchanges_processed: List[str] = []
