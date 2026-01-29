# -*- coding: utf-8 -*-
"""
History Models
기록용 데이터 모델
"""
from datetime import date, datetime
from typing import List, Optional
from decimal import Decimal
from enum import Enum

from pydantic import BaseModel, Field


# ============ 매매기록 감지 관련 모델 ============

class TradeType(str, Enum):
    """매매 유형"""
    BUY = "BUY"  # 추가 매수 (금일 수량 > 전일 수량)
    SELL = "SELL"  # 일부 매도 (금일 수량 < 전일 수량)
    NEW_BUY = "NEW_BUY"  # 신규 매수 (전일에 없고 금일에 존재)
    FULL_SELL = "FULL_SELL"  # 전량 매도 (전일에 있고 금일에 없거나 수량=0)


class TradeRecordCreate(BaseModel):
    """매매기록 생성 모델"""
    trade_date: date
    exchange: str
    currency: str
    ticker: str
    stock_name: Optional[str] = None
    trade_type: TradeType
    prev_quantity: Optional[Decimal] = None
    curr_quantity: Optional[Decimal] = None
    quantity_change: Decimal
    prev_price: Optional[Decimal] = None
    curr_price: Optional[Decimal] = None
    estimated_amount: Optional[Decimal] = None
    prev_record_date: Optional[date] = None
    detection_method: str = "AUTO"


class TradeRecord(TradeRecordCreate):
    """매매기록 조회 모델"""
    id: int
    created_at: datetime

    class Config:
        from_attributes = True


class TradeDetectionResult(BaseModel):
    """매매 감지 결과 모델"""
    trade_date: date
    prev_record_date: Optional[date] = None
    exchange: Optional[str] = None
    total_detected: int = 0
    new_buys: int = 0
    additional_buys: int = 0
    partial_sells: int = 0
    full_sells: int = 0
    records: List[TradeRecord] = []


class TradeSummary(BaseModel):
    """매매 요약 모델"""
    trade_date: date
    exchange: Optional[str] = None
    total_trades: int = 0
    new_buys: int = 0
    additional_buys: int = 0
    partial_sells: int = 0
    full_sells: int = 0
    total_buy_amount: Optional[Decimal] = None
    total_sell_amount: Optional[Decimal] = None


class TradeHistoryRequest(BaseModel):
    """매매기록 조회 요청"""
    start_date: Optional[date] = None
    end_date: Optional[date] = None
    exchange: Optional[str] = None
    ticker: Optional[str] = None
    trade_type: Optional[TradeType] = None
    limit: int = Field(default=100, le=1000)
    offset: int = Field(default=0, ge=0)


class TradeHistoryResponse(BaseModel):
    """매매기록 조회 응답"""
    records: List[TradeRecord]
    total_count: int
    limit: int
    offset: int


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


# ============ 자산 태그 관련 모델 ============

class AssetTagCreate(BaseModel):
    """자산 태그 생성 모델"""
    name: str = Field(..., min_length=1, max_length=50, description="태그 이름")
    category: Optional[str] = Field(None, max_length=30, description="태그 카테고리 (자산종류, 전략, 섹터 등)")
    color: Optional[str] = Field("#6B7280", pattern=r"^#[0-9A-Fa-f]{6}$", description="태그 색상 (HEX)")
    description: Optional[str] = Field(None, description="태그 설명")


class AssetTag(AssetTagCreate):
    """자산 태그 조회 모델"""
    id: int
    created_at: datetime

    class Config:
        from_attributes = True


class StockTagCreate(BaseModel):
    """종목 태그 연결 생성 모델"""
    ticker: str = Field(..., description="종목 코드")
    tag_id: int = Field(..., description="태그 ID")


class StockTag(StockTagCreate):
    """종목 태그 연결 조회 모델"""
    id: int
    created_at: datetime

    class Config:
        from_attributes = True


class StockWithTags(BaseModel):
    """태그가 포함된 종목 정보"""
    ticker: str
    stock_name: Optional[str] = None
    exchange: Optional[str] = None
    tags: List[AssetTag] = []


class TagWithStocks(BaseModel):
    """종목 목록이 포함된 태그 정보"""
    tag: AssetTag
    tickers: List[str] = []
    stock_count: int = 0


class BulkTagAssignRequest(BaseModel):
    """여러 종목에 태그 일괄 할당 요청"""
    tickers: List[str] = Field(..., min_length=1, description="종목 코드 목록")
    tag_ids: List[int] = Field(..., min_length=1, description="태그 ID 목록")


class TagListResponse(BaseModel):
    """태그 목록 응답"""
    tags: List[AssetTag]
    total_count: int


class StocksByTagResponse(BaseModel):
    """태그별 종목 목록 응답"""
    tag: AssetTag
    stocks: List[StockWithTags]
    total_count: int
