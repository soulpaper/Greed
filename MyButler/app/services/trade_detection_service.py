# -*- coding: utf-8 -*-
"""
Trade Detection Service
매매기록 자동 감지 서비스
"""
import logging
from datetime import date, datetime
from typing import List, Optional, Dict, Any, Tuple
from decimal import Decimal

from app.config.database_config import get_sqlite_connection
from app.utils.timezone_utils import format_date_for_db, parse_date_from_db
from app.models.history_models import (
    TradeType,
    TradeRecordCreate,
    TradeRecord,
    TradeDetectionResult,
    TradeSummary,
)

logger = logging.getLogger(__name__)


class TradeDetectionService:
    """매매기록 감지 서비스"""

    async def detect_trades(
        self,
        record_date: date,
        prev_date: Optional[date] = None,
        exchange: Optional[str] = None
    ) -> TradeDetectionResult:
        """
        전일 데이터와 비교하여 매매 감지

        Args:
            record_date: 기록 날짜 (금일)
            prev_date: 이전 기록 날짜 (None이면 자동 조회)
            exchange: 특정 거래소만 감지 (None이면 전체)

        Returns:
            TradeDetectionResult: 감지된 매매기록 결과
        """
        logger.info(f"매매 감지 시작: {record_date}, exchange={exchange}")

        # 이전 기록 날짜 조회
        if prev_date is None:
            prev_date = await self._get_previous_record_date(record_date, exchange)

        if prev_date is None:
            logger.info(f"이전 기록이 없어 매매 감지 스킵: {record_date}")
            return TradeDetectionResult(
                trade_date=record_date,
                prev_record_date=None,
                exchange=exchange,
                total_detected=0
            )

        # 양일 데이터 조회
        prev_data = await self._get_stock_data_by_date(prev_date, exchange)
        curr_data = await self._get_stock_data_by_date(record_date, exchange)

        # 매매 비교 및 감지
        trade_records = self._compare_and_detect(
            record_date=record_date,
            prev_date=prev_date,
            prev_data=prev_data,
            curr_data=curr_data
        )

        # 결과 저장
        if trade_records:
            saved_count = await self.save_trade_records(trade_records)
            logger.info(f"매매기록 저장 완료: {saved_count}건")

        # 통계 계산
        new_buys = sum(1 for r in trade_records if r.trade_type == TradeType.NEW_BUY)
        additional_buys = sum(1 for r in trade_records if r.trade_type == TradeType.BUY)
        partial_sells = sum(1 for r in trade_records if r.trade_type == TradeType.SELL)
        full_sells = sum(1 for r in trade_records if r.trade_type == TradeType.FULL_SELL)

        # TradeRecordCreate를 TradeRecord로 변환 (id, created_at 없이)
        # DB에서 저장된 후 조회하여 반환
        saved_records = await self._get_trade_records_by_date(record_date, exchange)

        result = TradeDetectionResult(
            trade_date=record_date,
            prev_record_date=prev_date,
            exchange=exchange,
            total_detected=len(trade_records),
            new_buys=new_buys,
            additional_buys=additional_buys,
            partial_sells=partial_sells,
            full_sells=full_sells,
            records=saved_records
        )

        logger.info(
            f"매매 감지 완료: {record_date}, "
            f"신규매수={new_buys}, 추가매수={additional_buys}, "
            f"일부매도={partial_sells}, 전량매도={full_sells}"
        )

        return result

    async def save_trade_records(self, records: List[TradeRecordCreate]) -> int:
        """매매기록 DB 저장 (upsert)"""
        if not records:
            return 0

        conn = await get_sqlite_connection()
        try:
            cursor = await conn.cursor()
            saved_count = 0

            for record in records:
                await cursor.execute("""
                    INSERT INTO trade_records
                    (trade_date, exchange, currency, ticker, stock_name, trade_type,
                     prev_quantity, curr_quantity, quantity_change, prev_price, curr_price,
                     estimated_amount, prev_record_date, detection_method)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    ON CONFLICT(trade_date, exchange, ticker, trade_type) DO UPDATE SET
                        stock_name = excluded.stock_name,
                        prev_quantity = excluded.prev_quantity,
                        curr_quantity = excluded.curr_quantity,
                        quantity_change = excluded.quantity_change,
                        prev_price = excluded.prev_price,
                        curr_price = excluded.curr_price,
                        estimated_amount = excluded.estimated_amount,
                        prev_record_date = excluded.prev_record_date,
                        detection_method = excluded.detection_method
                """, (
                    format_date_for_db(record.trade_date),
                    record.exchange,
                    record.currency,
                    record.ticker,
                    record.stock_name,
                    record.trade_type.value,
                    float(record.prev_quantity) if record.prev_quantity else None,
                    float(record.curr_quantity) if record.curr_quantity else None,
                    float(record.quantity_change),
                    float(record.prev_price) if record.prev_price else None,
                    float(record.curr_price) if record.curr_price else None,
                    float(record.estimated_amount) if record.estimated_amount else None,
                    format_date_for_db(record.prev_record_date) if record.prev_record_date else None,
                    record.detection_method,
                ))
                saved_count += 1

            await conn.commit()
            return saved_count
        finally:
            await conn.close()

    async def _get_previous_record_date(
        self,
        current_date: date,
        exchange: Optional[str] = None
    ) -> Optional[date]:
        """이전 기록 날짜 조회"""
        conn = await get_sqlite_connection()
        try:
            cursor = await conn.cursor()

            if exchange:
                await cursor.execute("""
                    SELECT MAX(record_date) FROM daily_stock_records
                    WHERE record_date < ? AND exchange = ?
                """, [format_date_for_db(current_date), exchange])
            else:
                await cursor.execute("""
                    SELECT MAX(record_date) FROM daily_stock_records
                    WHERE record_date < ?
                """, [format_date_for_db(current_date)])

            row = await cursor.fetchone()
            if row and row[0]:
                return parse_date_from_db(row[0])
            return None
        finally:
            await conn.close()

    async def _get_stock_data_by_date(
        self,
        record_date: date,
        exchange: Optional[str] = None
    ) -> Dict[str, Dict[str, Any]]:
        """특정 날짜의 종목 데이터 조회 (ticker를 키로 하는 dict)"""
        conn = await get_sqlite_connection()
        try:
            cursor = await conn.cursor()

            if exchange:
                await cursor.execute("""
                    SELECT ticker, stock_name, exchange, currency, quantity, current_price
                    FROM daily_stock_records
                    WHERE record_date = ? AND exchange = ?
                """, [format_date_for_db(record_date), exchange])
            else:
                await cursor.execute("""
                    SELECT ticker, stock_name, exchange, currency, quantity, current_price
                    FROM daily_stock_records
                    WHERE record_date = ?
                """, [format_date_for_db(record_date)])

            rows = await cursor.fetchall()
            result = {}
            for row in rows:
                # 동일 티커가 다른 거래소에 있을 수 있으므로 exchange 포함 키 사용
                key = f"{row['exchange']}:{row['ticker']}"
                result[key] = {
                    "ticker": row["ticker"],
                    "stock_name": row["stock_name"],
                    "exchange": row["exchange"],
                    "currency": row["currency"],
                    "quantity": Decimal(str(row["quantity"])) if row["quantity"] else Decimal("0"),
                    "current_price": Decimal(str(row["current_price"])) if row["current_price"] else None,
                }
            return result
        finally:
            await conn.close()

    def _compare_and_detect(
        self,
        record_date: date,
        prev_date: date,
        prev_data: Dict[str, Dict[str, Any]],
        curr_data: Dict[str, Dict[str, Any]]
    ) -> List[TradeRecordCreate]:
        """데이터 비교 및 매매 유형 결정"""
        trade_records = []

        all_keys = set(prev_data.keys()) | set(curr_data.keys())

        for key in all_keys:
            prev = prev_data.get(key)
            curr = curr_data.get(key)

            prev_qty = prev["quantity"] if prev else Decimal("0")
            curr_qty = curr["quantity"] if curr else Decimal("0")

            # 수량 변화 없으면 스킵
            if prev_qty == curr_qty:
                continue

            # 매매 유형 결정
            trade_type = self._determine_trade_type(prev_qty, curr_qty, prev is not None, curr is not None)
            if trade_type is None:
                continue

            quantity_change = curr_qty - prev_qty

            # 종목 정보 (금일 또는 전일에서)
            stock_info = curr if curr else prev
            exchange = stock_info["exchange"]
            currency = stock_info["currency"]
            ticker = stock_info["ticker"]
            stock_name = stock_info.get("stock_name")

            # 가격 정보
            prev_price = prev["current_price"] if prev else None
            curr_price = curr["current_price"] if curr else None

            # 추정 거래금액 계산
            estimated_amount = None
            if trade_type in [TradeType.BUY, TradeType.NEW_BUY]:
                # 매수: 금일가격 * 변화수량
                if curr_price:
                    estimated_amount = curr_price * abs(quantity_change)
            else:
                # 매도: 전일가격 * 변화수량 (전일가격 없으면 금일가격)
                price_for_calc = prev_price or curr_price
                if price_for_calc:
                    estimated_amount = price_for_calc * abs(quantity_change)

            trade_record = TradeRecordCreate(
                trade_date=record_date,
                exchange=exchange,
                currency=currency,
                ticker=ticker,
                stock_name=stock_name,
                trade_type=trade_type,
                prev_quantity=prev_qty if prev else None,
                curr_quantity=curr_qty if curr else None,
                quantity_change=quantity_change,
                prev_price=prev_price,
                curr_price=curr_price,
                estimated_amount=estimated_amount,
                prev_record_date=prev_date,
                detection_method="AUTO"
            )
            trade_records.append(trade_record)

        return trade_records

    def _determine_trade_type(
        self,
        prev_qty: Decimal,
        curr_qty: Decimal,
        existed_prev: bool,
        exists_curr: bool
    ) -> Optional[TradeType]:
        """
        매매 유형 결정

        | 유형 | 조건 |
        |------|------|
        | BUY | 금일 수량 > 전일 수량 (추가 매수) |
        | SELL | 금일 수량 < 전일 수량 (일부 매도) |
        | NEW_BUY | 전일에 없고 금일에 존재 (신규 매수) |
        | FULL_SELL | 전일에 있고 금일에 없거나 수량=0 (전량 매도) |
        """
        # 신규 매수: 전일에 없고 금일에 존재
        if not existed_prev and exists_curr and curr_qty > 0:
            return TradeType.NEW_BUY

        # 전량 매도: 전일에 있고 금일에 없거나 수량=0
        if existed_prev and prev_qty > 0 and (not exists_curr or curr_qty == 0):
            return TradeType.FULL_SELL

        # 추가 매수: 양쪽 다 존재하고 금일 > 전일
        if existed_prev and exists_curr and curr_qty > prev_qty:
            return TradeType.BUY

        # 일부 매도: 양쪽 다 존재하고 금일 < 전일
        if existed_prev and exists_curr and curr_qty < prev_qty and curr_qty > 0:
            return TradeType.SELL

        return None

    async def _get_trade_records_by_date(
        self,
        trade_date: date,
        exchange: Optional[str] = None
    ) -> List[TradeRecord]:
        """특정 날짜의 매매기록 조회"""
        conn = await get_sqlite_connection()
        try:
            cursor = await conn.cursor()

            if exchange:
                await cursor.execute("""
                    SELECT * FROM trade_records
                    WHERE trade_date = ? AND exchange = ?
                    ORDER BY ticker
                """, [format_date_for_db(trade_date), exchange])
            else:
                await cursor.execute("""
                    SELECT * FROM trade_records
                    WHERE trade_date = ?
                    ORDER BY exchange, ticker
                """, [format_date_for_db(trade_date)])

            rows = await cursor.fetchall()
            records = []
            for row in rows:
                records.append(TradeRecord(
                    id=row["id"],
                    trade_date=parse_date_from_db(row["trade_date"]),
                    exchange=row["exchange"],
                    currency=row["currency"],
                    ticker=row["ticker"],
                    stock_name=row["stock_name"],
                    trade_type=TradeType(row["trade_type"]),
                    prev_quantity=Decimal(str(row["prev_quantity"])) if row["prev_quantity"] else None,
                    curr_quantity=Decimal(str(row["curr_quantity"])) if row["curr_quantity"] else None,
                    quantity_change=Decimal(str(row["quantity_change"])),
                    prev_price=Decimal(str(row["prev_price"])) if row["prev_price"] else None,
                    curr_price=Decimal(str(row["curr_price"])) if row["curr_price"] else None,
                    estimated_amount=Decimal(str(row["estimated_amount"])) if row["estimated_amount"] else None,
                    prev_record_date=parse_date_from_db(row["prev_record_date"]) if row["prev_record_date"] else None,
                    detection_method=row["detection_method"],
                    created_at=datetime.fromisoformat(row["created_at"]) if row["created_at"] else datetime.now(),
                ))
            return records
        finally:
            await conn.close()

    async def get_trade_summary(
        self,
        trade_date: date,
        exchange: Optional[str] = None
    ) -> TradeSummary:
        """특정 날짜의 매매 요약 조회"""
        conn = await get_sqlite_connection()
        try:
            cursor = await conn.cursor()

            if exchange:
                await cursor.execute("""
                    SELECT
                        trade_type,
                        COUNT(*) as count,
                        SUM(ABS(estimated_amount)) as total_amount
                    FROM trade_records
                    WHERE trade_date = ? AND exchange = ?
                    GROUP BY trade_type
                """, [format_date_for_db(trade_date), exchange])
            else:
                await cursor.execute("""
                    SELECT
                        trade_type,
                        COUNT(*) as count,
                        SUM(ABS(estimated_amount)) as total_amount
                    FROM trade_records
                    WHERE trade_date = ?
                    GROUP BY trade_type
                """, [format_date_for_db(trade_date)])

            rows = await cursor.fetchall()

            new_buys = 0
            additional_buys = 0
            partial_sells = 0
            full_sells = 0
            total_buy_amount = Decimal("0")
            total_sell_amount = Decimal("0")

            for row in rows:
                trade_type = row["trade_type"]
                count = row["count"]
                amount = Decimal(str(row["total_amount"])) if row["total_amount"] else Decimal("0")

                if trade_type == TradeType.NEW_BUY.value:
                    new_buys = count
                    total_buy_amount += amount
                elif trade_type == TradeType.BUY.value:
                    additional_buys = count
                    total_buy_amount += amount
                elif trade_type == TradeType.SELL.value:
                    partial_sells = count
                    total_sell_amount += amount
                elif trade_type == TradeType.FULL_SELL.value:
                    full_sells = count
                    total_sell_amount += amount

            return TradeSummary(
                trade_date=trade_date,
                exchange=exchange,
                total_trades=new_buys + additional_buys + partial_sells + full_sells,
                new_buys=new_buys,
                additional_buys=additional_buys,
                partial_sells=partial_sells,
                full_sells=full_sells,
                total_buy_amount=total_buy_amount if total_buy_amount > 0 else None,
                total_sell_amount=total_sell_amount if total_sell_amount > 0 else None,
            )
        finally:
            await conn.close()


def get_trade_detection_service() -> TradeDetectionService:
    """매매 감지 서비스 인스턴스 생성"""
    return TradeDetectionService()
