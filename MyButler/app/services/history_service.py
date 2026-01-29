# -*- coding: utf-8 -*-
"""
History Service
SQLite 히스토리 조회 서비스
"""
import logging
from datetime import date, datetime
from typing import List, Optional, Dict, Any, Tuple
from decimal import Decimal

from app.config.database_config import get_sqlite_connection
from app.utils.timezone_utils import format_date_for_db, parse_date_from_db
from app.models.history_models import (
    StockRecord,
    SummaryRecord,
    RecordingLog,
    StockRecordCreate,
    SummaryRecordCreate,
    TradeType,
    TradeRecord,
    TradeSummary,
)

logger = logging.getLogger(__name__)


class HistoryService:
    """히스토리 조회 서비스"""

    async def save_stock_records(self, records: List[StockRecordCreate]) -> int:
        """종목 기록 저장 (upsert)"""
        if not records:
            return 0

        conn = await get_sqlite_connection()
        try:
            cursor = await conn.cursor()
            saved_count = 0

            for record in records:
                await cursor.execute("""
                    INSERT INTO daily_stock_records
                    (record_date, exchange, currency, ticker, stock_name, quantity,
                     avg_purchase_price, current_price, purchase_amount, eval_amount,
                     profit_loss_amount, profit_loss_rate)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    ON CONFLICT(record_date, exchange, ticker) DO UPDATE SET
                        stock_name = excluded.stock_name,
                        quantity = excluded.quantity,
                        avg_purchase_price = excluded.avg_purchase_price,
                        current_price = excluded.current_price,
                        purchase_amount = excluded.purchase_amount,
                        eval_amount = excluded.eval_amount,
                        profit_loss_amount = excluded.profit_loss_amount,
                        profit_loss_rate = excluded.profit_loss_rate
                """, (
                    format_date_for_db(record.record_date),
                    record.exchange,
                    record.currency,
                    record.ticker,
                    record.stock_name,
                    float(record.quantity) if record.quantity else None,
                    float(record.avg_purchase_price) if record.avg_purchase_price else None,
                    float(record.current_price) if record.current_price else None,
                    float(record.purchase_amount) if record.purchase_amount else None,
                    float(record.eval_amount) if record.eval_amount else None,
                    float(record.profit_loss_amount) if record.profit_loss_amount else None,
                    float(record.profit_loss_rate) if record.profit_loss_rate else None,
                ))
                saved_count += 1

            await conn.commit()
            logger.info(f"종목 기록 저장 완료: {saved_count}개")
            return saved_count
        finally:
            await conn.close()

    async def save_summary_record(self, record: SummaryRecordCreate) -> bool:
        """계좌 요약 기록 저장 (upsert)"""
        conn = await get_sqlite_connection()
        try:
            cursor = await conn.cursor()

            await cursor.execute("""
                INSERT INTO daily_summary_records
                (record_date, exchange, currency, total_purchase_amount, total_eval_amount,
                 total_profit_loss, total_profit_rate, stock_count)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(record_date, exchange) DO UPDATE SET
                    currency = excluded.currency,
                    total_purchase_amount = excluded.total_purchase_amount,
                    total_eval_amount = excluded.total_eval_amount,
                    total_profit_loss = excluded.total_profit_loss,
                    total_profit_rate = excluded.total_profit_rate,
                    stock_count = excluded.stock_count
            """, (
                format_date_for_db(record.record_date),
                record.exchange,
                record.currency,
                float(record.total_purchase_amount) if record.total_purchase_amount else None,
                float(record.total_eval_amount) if record.total_eval_amount else None,
                float(record.total_profit_loss) if record.total_profit_loss else None,
                float(record.total_profit_rate) if record.total_profit_rate else None,
                record.stock_count,
            ))

            await conn.commit()
            logger.info(f"요약 기록 저장 완료: {record.exchange}/{record.record_date}")
            return True
        finally:
            await conn.close()

    async def get_stock_records(
        self,
        start_date: Optional[date] = None,
        end_date: Optional[date] = None,
        exchange: Optional[str] = None,
        ticker: Optional[str] = None,
        limit: int = 100,
        offset: int = 0
    ) -> Tuple[List[StockRecord], int]:
        """종목 기록 조회"""
        conn = await get_sqlite_connection()
        try:
            cursor = await conn.cursor()

            where_clauses = []
            params = []

            if start_date:
                where_clauses.append("record_date >= ?")
                params.append(format_date_for_db(start_date))
            if end_date:
                where_clauses.append("record_date <= ?")
                params.append(format_date_for_db(end_date))
            if exchange:
                where_clauses.append("exchange = ?")
                params.append(exchange)
            if ticker:
                where_clauses.append("ticker = ?")
                params.append(ticker)

            where_sql = " AND ".join(where_clauses) if where_clauses else "1=1"

            # 총 개수 조회
            await cursor.execute(f"SELECT COUNT(*) FROM daily_stock_records WHERE {where_sql}", params)
            total_count = (await cursor.fetchone())[0]

            # 데이터 조회
            await cursor.execute(f"""
                SELECT * FROM daily_stock_records
                WHERE {where_sql}
                ORDER BY record_date DESC, exchange, ticker
                LIMIT ? OFFSET ?
            """, params + [limit, offset])

            rows = await cursor.fetchall()
            records = []
            for row in rows:
                records.append(StockRecord(
                    id=row["id"],
                    record_date=parse_date_from_db(row["record_date"]),
                    exchange=row["exchange"],
                    currency=row["currency"],
                    ticker=row["ticker"],
                    stock_name=row["stock_name"],
                    quantity=Decimal(str(row["quantity"])) if row["quantity"] else None,
                    avg_purchase_price=Decimal(str(row["avg_purchase_price"])) if row["avg_purchase_price"] else None,
                    current_price=Decimal(str(row["current_price"])) if row["current_price"] else None,
                    purchase_amount=Decimal(str(row["purchase_amount"])) if row["purchase_amount"] else None,
                    eval_amount=Decimal(str(row["eval_amount"])) if row["eval_amount"] else None,
                    profit_loss_amount=Decimal(str(row["profit_loss_amount"])) if row["profit_loss_amount"] else None,
                    profit_loss_rate=Decimal(str(row["profit_loss_rate"])) if row["profit_loss_rate"] else None,
                    created_at=datetime.fromisoformat(row["created_at"]) if row["created_at"] else datetime.now(),
                ))

            return records, total_count
        finally:
            await conn.close()

    async def get_summary_records(
        self,
        start_date: Optional[date] = None,
        end_date: Optional[date] = None,
        exchange: Optional[str] = None,
        limit: int = 100,
        offset: int = 0
    ) -> Tuple[List[SummaryRecord], int]:
        """요약 기록 조회"""
        conn = await get_sqlite_connection()
        try:
            cursor = await conn.cursor()

            where_clauses = []
            params = []

            if start_date:
                where_clauses.append("record_date >= ?")
                params.append(format_date_for_db(start_date))
            if end_date:
                where_clauses.append("record_date <= ?")
                params.append(format_date_for_db(end_date))
            if exchange:
                where_clauses.append("exchange = ?")
                params.append(exchange)

            where_sql = " AND ".join(where_clauses) if where_clauses else "1=1"

            # 총 개수 조회
            await cursor.execute(f"SELECT COUNT(*) FROM daily_summary_records WHERE {where_sql}", params)
            total_count = (await cursor.fetchone())[0]

            # 데이터 조회
            await cursor.execute(f"""
                SELECT * FROM daily_summary_records
                WHERE {where_sql}
                ORDER BY record_date DESC, exchange
                LIMIT ? OFFSET ?
            """, params + [limit, offset])

            rows = await cursor.fetchall()
            records = []
            for row in rows:
                records.append(SummaryRecord(
                    id=row["id"],
                    record_date=parse_date_from_db(row["record_date"]),
                    exchange=row["exchange"],
                    currency=row["currency"],
                    total_purchase_amount=Decimal(str(row["total_purchase_amount"])) if row["total_purchase_amount"] else None,
                    total_eval_amount=Decimal(str(row["total_eval_amount"])) if row["total_eval_amount"] else None,
                    total_profit_loss=Decimal(str(row["total_profit_loss"])) if row["total_profit_loss"] else None,
                    total_profit_rate=Decimal(str(row["total_profit_rate"])) if row["total_profit_rate"] else None,
                    stock_count=row["stock_count"],
                    created_at=datetime.fromisoformat(row["created_at"]) if row["created_at"] else datetime.now(),
                ))

            return records, total_count
        finally:
            await conn.close()

    async def get_stock_by_ticker(
        self,
        ticker: str,
        start_date: Optional[date] = None,
        end_date: Optional[date] = None,
        limit: int = 100
    ) -> List[StockRecord]:
        """특정 종목 히스토리 조회"""
        records, _ = await self.get_stock_records(
            start_date=start_date,
            end_date=end_date,
            ticker=ticker,
            limit=limit
        )
        return records

    async def get_latest_record_date(self) -> Optional[date]:
        """가장 최근 기록 날짜 조회"""
        conn = await get_sqlite_connection()
        try:
            cursor = await conn.cursor()
            await cursor.execute("SELECT MAX(record_date) FROM daily_stock_records")
            row = await cursor.fetchone()
            if row and row[0]:
                return parse_date_from_db(row[0])
            return None
        finally:
            await conn.close()

    async def get_latest_records(self) -> Dict[str, Any]:
        """최신 기록 데이터 조회"""
        latest_date = await self.get_latest_record_date()
        if not latest_date:
            return {"record_date": None, "exchanges": {}, "total_stocks": 0}

        conn = await get_sqlite_connection()
        try:
            cursor = await conn.cursor()

            # 거래소별 요약 조회
            await cursor.execute("""
                SELECT exchange, currency, COUNT(*) as count,
                       SUM(profit_loss_amount) as total_pnl
                FROM daily_stock_records
                WHERE record_date = ?
                GROUP BY exchange
            """, [format_date_for_db(latest_date)])

            exchanges = {}
            total_stocks = 0
            async for row in cursor:
                exchanges[row["exchange"]] = {
                    "currency": row["currency"],
                    "count": row["count"],
                    "total_profit_loss": float(row["total_pnl"]) if row["total_pnl"] else 0
                }
                total_stocks += row["count"]

            return {
                "record_date": latest_date,
                "exchanges": exchanges,
                "total_stocks": total_stocks
            }
        finally:
            await conn.close()

    async def compare_dates(
        self,
        date1: date,
        date2: date,
        exchange: Optional[str] = None
    ) -> Dict[str, Any]:
        """두 날짜 데이터 비교"""
        conn = await get_sqlite_connection()
        try:
            cursor = await conn.cursor()

            exchange_filter = "AND exchange = ?" if exchange else ""
            params1 = [format_date_for_db(date1)] + ([exchange] if exchange else [])
            params2 = [format_date_for_db(date2)] + ([exchange] if exchange else [])

            # date1 데이터
            await cursor.execute(f"""
                SELECT ticker, stock_name, exchange, current_price, quantity, profit_loss_amount
                FROM daily_stock_records
                WHERE record_date = ? {exchange_filter}
            """, params1)
            date1_data = {row["ticker"]: dict(row) for row in await cursor.fetchall()}

            # date2 데이터
            await cursor.execute(f"""
                SELECT ticker, stock_name, exchange, current_price, quantity, profit_loss_amount
                FROM daily_stock_records
                WHERE record_date = ? {exchange_filter}
            """, params2)
            date2_data = {row["ticker"]: dict(row) for row in await cursor.fetchall()}

            # 비교
            all_tickers = set(date1_data.keys()) | set(date2_data.keys())
            comparisons = []

            for ticker in all_tickers:
                d1 = date1_data.get(ticker, {})
                d2 = date2_data.get(ticker, {})

                d1_price = d1.get("current_price")
                d2_price = d2.get("current_price")
                price_change = None
                price_change_rate = None

                if d1_price and d2_price:
                    price_change = float(d2_price) - float(d1_price)
                    if float(d1_price) != 0:
                        price_change_rate = (price_change / float(d1_price)) * 100

                comparisons.append({
                    "ticker": ticker,
                    "stock_name": d2.get("stock_name") or d1.get("stock_name"),
                    "exchange": d2.get("exchange") or d1.get("exchange"),
                    "date1_price": d1_price,
                    "date2_price": d2_price,
                    "price_change": price_change,
                    "price_change_rate": price_change_rate,
                    "date1_quantity": d1.get("quantity"),
                    "date2_quantity": d2.get("quantity"),
                    "quantity_change": (float(d2.get("quantity") or 0) - float(d1.get("quantity") or 0)) if d1.get("quantity") or d2.get("quantity") else None,
                })

            # 요약
            added = len(set(date2_data.keys()) - set(date1_data.keys()))
            removed = len(set(date1_data.keys()) - set(date2_data.keys()))

            return {
                "date1": date1,
                "date2": date2,
                "comparisons": comparisons,
                "summary": {
                    "total_tickers": len(all_tickers),
                    "added": added,
                    "removed": removed,
                    "unchanged": len(all_tickers) - added - removed
                }
            }
        finally:
            await conn.close()

    async def create_recording_log(self, record_date: date) -> int:
        """기록 로그 생성"""
        conn = await get_sqlite_connection()
        try:
            cursor = await conn.cursor()
            await cursor.execute("""
                INSERT INTO recording_logs (record_date, status)
                VALUES (?, 'STARTED')
                ON CONFLICT(record_date) DO UPDATE SET
                    started_at = CURRENT_TIMESTAMP,
                    status = 'STARTED',
                    completed_at = NULL,
                    error_message = NULL
            """, [format_date_for_db(record_date)])
            await conn.commit()
            return cursor.lastrowid
        finally:
            await conn.close()

    async def update_recording_log(
        self,
        record_date: date,
        status: str,
        exchanges_processed: Optional[List[str]] = None,
        total_stocks: int = 0,
        error_message: Optional[str] = None
    ) -> bool:
        """기록 로그 업데이트"""
        conn = await get_sqlite_connection()
        try:
            cursor = await conn.cursor()
            await cursor.execute("""
                UPDATE recording_logs
                SET status = ?,
                    completed_at = CURRENT_TIMESTAMP,
                    exchanges_processed = ?,
                    total_stocks = ?,
                    error_message = ?
                WHERE record_date = ?
            """, [
                status,
                ",".join(exchanges_processed) if exchanges_processed else None,
                total_stocks,
                error_message,
                format_date_for_db(record_date)
            ])
            await conn.commit()
            return True
        finally:
            await conn.close()

    async def get_recording_logs(self, limit: int = 10) -> List[RecordingLog]:
        """기록 로그 조회"""
        conn = await get_sqlite_connection()
        try:
            cursor = await conn.cursor()
            await cursor.execute("""
                SELECT * FROM recording_logs
                ORDER BY record_date DESC
                LIMIT ?
            """, [limit])

            logs = []
            async for row in cursor:
                logs.append(RecordingLog(
                    id=row["id"],
                    record_date=parse_date_from_db(row["record_date"]),
                    started_at=datetime.fromisoformat(row["started_at"]) if row["started_at"] else datetime.now(),
                    completed_at=datetime.fromisoformat(row["completed_at"]) if row["completed_at"] else None,
                    status=row["status"],
                    exchanges_processed=row["exchanges_processed"],
                    total_stocks=row["total_stocks"] or 0,
                    error_message=row["error_message"]
                ))
            return logs
        finally:
            await conn.close()

    # ============ 매매기록 조회 메서드 ============

    async def get_trade_records(
        self,
        start_date: Optional[date] = None,
        end_date: Optional[date] = None,
        exchange: Optional[str] = None,
        ticker: Optional[str] = None,
        trade_type: Optional[TradeType] = None,
        limit: int = 100,
        offset: int = 0
    ) -> Tuple[List[TradeRecord], int]:
        """매매기록 조회"""
        conn = await get_sqlite_connection()
        try:
            cursor = await conn.cursor()

            where_clauses = []
            params = []

            if start_date:
                where_clauses.append("trade_date >= ?")
                params.append(format_date_for_db(start_date))
            if end_date:
                where_clauses.append("trade_date <= ?")
                params.append(format_date_for_db(end_date))
            if exchange:
                where_clauses.append("exchange = ?")
                params.append(exchange)
            if ticker:
                where_clauses.append("ticker = ?")
                params.append(ticker)
            if trade_type:
                where_clauses.append("trade_type = ?")
                params.append(trade_type.value)

            where_sql = " AND ".join(where_clauses) if where_clauses else "1=1"

            # 총 개수 조회
            await cursor.execute(f"SELECT COUNT(*) FROM trade_records WHERE {where_sql}", params)
            total_count = (await cursor.fetchone())[0]

            # 데이터 조회
            await cursor.execute(f"""
                SELECT * FROM trade_records
                WHERE {where_sql}
                ORDER BY trade_date DESC, exchange, ticker
                LIMIT ? OFFSET ?
            """, params + [limit, offset])

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

            return records, total_count
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
                trade_type_val = row["trade_type"]
                count = row["count"]
                amount = Decimal(str(row["total_amount"])) if row["total_amount"] else Decimal("0")

                if trade_type_val == TradeType.NEW_BUY.value:
                    new_buys = count
                    total_buy_amount += amount
                elif trade_type_val == TradeType.BUY.value:
                    additional_buys = count
                    total_buy_amount += amount
                elif trade_type_val == TradeType.SELL.value:
                    partial_sells = count
                    total_sell_amount += amount
                elif trade_type_val == TradeType.FULL_SELL.value:
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


def get_history_service() -> HistoryService:
    """히스토리 서비스 인스턴스 생성"""
    return HistoryService()
