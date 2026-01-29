# -*- coding: utf-8 -*-
"""
Recording Service
일일 주식 기록 비즈니스 로직
"""
import logging
from datetime import date
from decimal import Decimal
from typing import Dict, Any, List, Optional

from app.config.scheduler_config import get_scheduler_config
from app.services.balance_service import get_balance_service
from app.services.history_service import get_history_service
from app.services.redis_service import get_redis_service
from app.models.history_models import StockRecordCreate, SummaryRecordCreate
from app.utils.market_calendar import should_record_today, get_holiday_name
from app.utils.timezone_utils import get_trading_date_for_recording, format_date_for_db

logger = logging.getLogger(__name__)


class RecordingService:
    """일일 주식 기록 서비스"""

    def __init__(self):
        self.scheduler_config = get_scheduler_config()
        self.balance_service = get_balance_service()
        self.history_service = get_history_service()
        self.redis_service = get_redis_service()

    def _parse_decimal(self, value: Any) -> Optional[Decimal]:
        """값을 Decimal로 파싱"""
        if value is None or value == "" or value == "0":
            return None
        try:
            return Decimal(str(value))
        except Exception:
            return None

    def _convert_overseas_stock_to_record(
        self,
        stock_data: Dict[str, Any],
        record_date: date,
        exchange: str,
        currency: str
    ) -> StockRecordCreate:
        """해외 주식 데이터를 기록 모델로 변환"""
        return StockRecordCreate(
            record_date=record_date,
            exchange=exchange,
            currency=currency,
            ticker=stock_data.get("ovrs_pdno", ""),
            stock_name=stock_data.get("ovrs_item_name", ""),
            quantity=self._parse_decimal(stock_data.get("ovrs_cblc_qty")),
            avg_purchase_price=self._parse_decimal(stock_data.get("pchs_avg_pric")),
            current_price=self._parse_decimal(stock_data.get("now_pric2")),
            purchase_amount=self._parse_decimal(stock_data.get("frcr_pchs_amt1")),
            eval_amount=self._parse_decimal(stock_data.get("ovrs_stck_evlu_amt")),
            profit_loss_amount=self._parse_decimal(stock_data.get("frcr_evlu_pfls_amt")),
            profit_loss_rate=self._parse_decimal(stock_data.get("evlu_pfls_rt")),
        )

    def _convert_overseas_summary_to_record(
        self,
        summary_data: Dict[str, Any],
        record_date: date,
        exchange: str,
        currency: str,
        stock_count: int
    ) -> SummaryRecordCreate:
        """해외 계좌 요약 데이터를 기록 모델로 변환"""
        return SummaryRecordCreate(
            record_date=record_date,
            exchange=exchange,
            currency=currency,
            total_purchase_amount=self._parse_decimal(summary_data.get("frcr_pchs_amt1")),
            total_eval_amount=self._parse_decimal(summary_data.get("tot_evlu_pfls_amt")),
            total_profit_loss=self._parse_decimal(summary_data.get("ovrs_tot_pfls")),
            total_profit_rate=self._parse_decimal(summary_data.get("tot_pftrt")),
            stock_count=stock_count,
        )

    def _convert_domestic_stock_to_record(
        self,
        stock_data: Dict[str, Any],
        record_date: date,
    ) -> StockRecordCreate:
        """국내 주식 데이터를 기록 모델로 변환"""
        return StockRecordCreate(
            record_date=record_date,
            exchange="KRX",
            currency="KRW",
            ticker=stock_data.get("pdno", ""),
            stock_name=stock_data.get("prdt_name", ""),
            quantity=self._parse_decimal(stock_data.get("hldg_qty")),
            avg_purchase_price=self._parse_decimal(stock_data.get("pchs_avg_pric")),
            current_price=self._parse_decimal(stock_data.get("prpr")),
            purchase_amount=self._parse_decimal(stock_data.get("pchs_amt")),
            eval_amount=self._parse_decimal(stock_data.get("evlu_amt")),
            profit_loss_amount=self._parse_decimal(stock_data.get("evlu_pfls_amt")),
            profit_loss_rate=self._parse_decimal(stock_data.get("evlu_pfls_rt")),
        )

    def _convert_domestic_summary_to_record(
        self,
        summary_data: Dict[str, Any],
        record_date: date,
        stock_count: int
    ) -> SummaryRecordCreate:
        """국내 계좌 요약 데이터를 기록 모델로 변환"""
        return SummaryRecordCreate(
            record_date=record_date,
            exchange="KRX",
            currency="KRW",
            total_purchase_amount=self._parse_decimal(summary_data.get("pchs_amt_smtl_amt")),
            total_eval_amount=self._parse_decimal(summary_data.get("evlu_amt_smtl_amt")),
            total_profit_loss=self._parse_decimal(summary_data.get("evlu_pfls_smtl_amt")),
            total_profit_rate=self._parse_decimal(summary_data.get("tot_evlu_pfls_rt")),
            stock_count=stock_count,
        )

    async def record_exchange(
        self,
        exchange: str,
        currency: str,
        record_date: date
    ) -> Dict[str, Any]:
        """단일 거래소 기록"""
        logger.info(f"거래소 기록 시작: {exchange} ({currency}) - {record_date}")

        try:
            # 잔고 조회
            stocks_df, summary_df = self.balance_service.get_overseas_balance(
                ovrs_excg_cd=exchange,
                tr_crcy_cd=currency
            )

            stock_records = []
            stocks_for_redis = []

            # 종목 데이터 변환
            if not stocks_df.empty:
                for _, row in stocks_df.iterrows():
                    stock_data = row.to_dict()
                    stocks_for_redis.append(stock_data)

                    record = self._convert_overseas_stock_to_record(
                        stock_data, record_date, exchange, currency
                    )
                    stock_records.append(record)

            # 요약 데이터 변환
            summary_record = None
            summary_for_redis = {}
            if not summary_df.empty:
                summary_data = summary_df.iloc[0].to_dict()
                summary_for_redis = summary_data

                summary_record = self._convert_overseas_summary_to_record(
                    summary_data, record_date, exchange, currency, len(stock_records)
                )

            # Redis에 캐시 저장
            await self.redis_service.save_stock_records(exchange, record_date, stocks_for_redis)
            if summary_for_redis:
                await self.redis_service.save_summary_record(exchange, record_date, summary_for_redis)
            await self.redis_service.set_latest_date(exchange, record_date)

            # SQLite에 영구 저장
            saved_count = await self.history_service.save_stock_records(stock_records)
            if summary_record:
                await self.history_service.save_summary_record(summary_record)

            logger.info(f"거래소 기록 완료: {exchange} - {saved_count}개 종목")

            return {
                "exchange": exchange,
                "currency": currency,
                "success": True,
                "stock_count": saved_count,
                "error": None
            }

        except Exception as e:
            logger.error(f"거래소 기록 실패: {exchange} - {str(e)}")
            return {
                "exchange": exchange,
                "currency": currency,
                "success": False,
                "stock_count": 0,
                "error": str(e)
            }

    async def record_all_exchanges(
        self,
        record_date: Optional[date] = None,
        target_exchanges: Optional[List[str]] = None
    ) -> Dict[str, Any]:
        """모든 대상 거래소 기록"""
        if record_date is None:
            record_date = get_trading_date_for_recording()

        # 거래일 확인
        if not should_record_today(record_date):
            holiday_name = get_holiday_name(record_date, "US")
            message = f"휴장일입니다: {record_date}"
            if holiday_name:
                message += f" ({holiday_name})"
            logger.info(message)
            return {
                "success": True,
                "skipped": True,
                "message": message,
                "record_date": record_date,
                "exchanges_processed": [],
                "total_stocks": 0
            }

        logger.info(f"일일 기록 시작: {record_date}")

        # 기록 로그 생성
        await self.history_service.create_recording_log(record_date)

        # Redis 상태 업데이트
        await self.redis_service.set_recording_status({
            "is_running": True,
            "started_at": format_date_for_db(record_date),
            "current_exchange": None
        })

        # 대상 거래소 결정
        exchanges_to_process = self.scheduler_config.target_exchanges
        if target_exchanges:
            exchanges_to_process = [
                (ex, curr, name) for ex, curr, name in self.scheduler_config.target_exchanges
                if ex in target_exchanges
            ]

        results = []
        total_stocks = 0
        success_exchanges = []
        failed_exchanges = []

        for exchange, currency, name in exchanges_to_process:
            # 상태 업데이트
            await self.redis_service.set_recording_status({
                "is_running": True,
                "current_exchange": exchange
            })

            result = await self.record_exchange(exchange, currency, record_date)
            results.append(result)

            if result["success"]:
                success_exchanges.append(exchange)
                total_stocks += result["stock_count"]
            else:
                failed_exchanges.append(exchange)

        # 최종 상태 결정
        if not failed_exchanges:
            status = "SUCCESS"
        elif not success_exchanges:
            status = "FAILED"
        else:
            status = "PARTIAL"

        # 기록 로그 업데이트
        error_message = None
        if failed_exchanges:
            error_message = f"Failed exchanges: {', '.join(failed_exchanges)}"

        await self.history_service.update_recording_log(
            record_date=record_date,
            status=status,
            exchanges_processed=success_exchanges,
            total_stocks=total_stocks,
            error_message=error_message
        )

        # Redis 상태 초기화
        await self.redis_service.set_recording_status({
            "is_running": False,
            "last_record_date": format_date_for_db(record_date),
            "last_status": status
        })

        logger.info(f"일일 기록 완료: {status} - {total_stocks}개 종목")

        return {
            "success": status != "FAILED",
            "skipped": False,
            "status": status,
            "record_date": record_date,
            "exchanges_processed": success_exchanges,
            "failed_exchanges": failed_exchanges,
            "total_stocks": total_stocks,
            "results": results
        }

    async def get_recording_status(self) -> Dict[str, Any]:
        """기록 작업 상태 조회"""
        redis_status = await self.redis_service.get_recording_status()
        logs = await self.history_service.get_recording_logs(limit=1)

        return {
            "is_running": redis_status.get("is_running", False),
            "current_exchange": redis_status.get("current_exchange"),
            "last_record_date": redis_status.get("last_record_date"),
            "last_status": redis_status.get("last_status"),
            "last_log": logs[0] if logs else None
        }

    # ========== 국내주식 기록 ==========

    async def record_domestic(
        self,
        record_date: Optional[date] = None
    ) -> Dict[str, Any]:
        """
        국내주식 잔고 기록

        Args:
            record_date: 기록 날짜 (None이면 오늘)

        Returns:
            기록 결과
        """
        if record_date is None:
            record_date = date.today()

        logger.info(f"국내주식 기록 시작: {record_date}")

        # 한국 거래일 확인
        if not should_record_today(record_date, market="KR"):
            holiday_name = get_holiday_name(record_date, "KR")
            message = f"한국 휴장일입니다: {record_date}"
            if holiday_name:
                message += f" ({holiday_name})"
            logger.info(message)
            return {
                "success": True,
                "skipped": True,
                "message": message,
                "record_date": record_date,
                "stock_count": 0
            }

        try:
            # 국내주식 잔고 조회
            stocks_df, summary_df = self.balance_service.get_domestic_balance()

            stock_records = []
            stocks_for_redis = []

            # 종목 데이터 변환
            if not stocks_df.empty:
                for _, row in stocks_df.iterrows():
                    stock_data = row.to_dict()
                    # 보유수량이 0인 종목 제외
                    if self._parse_decimal(stock_data.get("hldg_qty")) in (None, Decimal("0")):
                        continue
                    stocks_for_redis.append(stock_data)
                    record = self._convert_domestic_stock_to_record(stock_data, record_date)
                    stock_records.append(record)

            # 요약 데이터 변환
            summary_record = None
            summary_for_redis = {}
            if not summary_df.empty:
                summary_data = summary_df.iloc[0].to_dict()
                summary_for_redis = summary_data
                summary_record = self._convert_domestic_summary_to_record(
                    summary_data, record_date, len(stock_records)
                )

            # Redis에 캐시 저장
            await self.redis_service.save_stock_records("KRX", record_date, stocks_for_redis)
            if summary_for_redis:
                await self.redis_service.save_summary_record("KRX", record_date, summary_for_redis)
            await self.redis_service.set_latest_date("KRX", record_date)

            # SQLite에 영구 저장
            saved_count = await self.history_service.save_stock_records(stock_records)
            if summary_record:
                await self.history_service.save_summary_record(summary_record)

            logger.info(f"국내주식 기록 완료: {saved_count}개 종목")

            return {
                "success": True,
                "skipped": False,
                "record_date": record_date,
                "exchange": "KRX",
                "currency": "KRW",
                "stock_count": saved_count,
                "error": None
            }

        except Exception as e:
            logger.error(f"국내주식 기록 실패: {str(e)}", exc_info=True)
            return {
                "success": False,
                "skipped": False,
                "record_date": record_date,
                "exchange": "KRX",
                "currency": "KRW",
                "stock_count": 0,
                "error": str(e)
            }


def get_recording_service() -> RecordingService:
    """기록 서비스 인스턴스 생성"""
    return RecordingService()
