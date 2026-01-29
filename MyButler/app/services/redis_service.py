# -*- coding: utf-8 -*-
"""
Redis Service
Redis 캐시 서비스
"""
import json
import logging
from datetime import date
from typing import Dict, List, Optional, Any

from app.config.database_config import get_redis_connection, get_database_config
from app.utils.timezone_utils import format_date_for_db

logger = logging.getLogger(__name__)


class RedisService:
    """Redis 캐시 서비스"""

    # Redis 키 프리픽스
    KEY_PREFIX = "mybutler"
    STOCK_KEY = f"{KEY_PREFIX}:stock"
    SUMMARY_KEY = f"{KEY_PREFIX}:summary"
    LATEST_KEY = f"{KEY_PREFIX}:latest"
    STATUS_KEY = f"{KEY_PREFIX}:recording:status"

    def __init__(self):
        self.config = get_database_config()

    async def _get_redis(self):
        """Redis 연결 가져오기"""
        return await get_redis_connection()

    def _stock_key(self, exchange: str, record_date: date) -> str:
        """종목 데이터 키 생성"""
        return f"{self.STOCK_KEY}:{exchange}:{format_date_for_db(record_date)}"

    def _summary_key(self, exchange: str, record_date: date) -> str:
        """요약 데이터 키 생성"""
        return f"{self.SUMMARY_KEY}:{exchange}:{format_date_for_db(record_date)}"

    def _latest_key(self, exchange: str) -> str:
        """최신 기록 날짜 키 생성"""
        return f"{self.LATEST_KEY}:{exchange}"

    async def save_stock_records(
        self,
        exchange: str,
        record_date: date,
        stocks: List[Dict[str, Any]]
    ) -> bool:
        """종목 데이터 저장"""
        try:
            redis = await self._get_redis()
            key = self._stock_key(exchange, record_date)

            # Hash로 저장 (ticker를 field로 사용)
            if stocks:
                stock_data = {stock.get("ticker", stock.get("ovrs_pdno", "")): json.dumps(stock, default=str) for stock in stocks}
                await redis.hset(key, mapping=stock_data)
                await redis.expire(key, self.config.redis_ttl_seconds)

            logger.info(f"Redis에 종목 데이터 저장 완료: {exchange}/{record_date} ({len(stocks)}개)")
            return True
        except Exception as e:
            logger.error(f"Redis 종목 데이터 저장 실패: {e}")
            return False

    async def get_stock_records(
        self,
        exchange: str,
        record_date: date
    ) -> List[Dict[str, Any]]:
        """종목 데이터 조회"""
        try:
            redis = await self._get_redis()
            key = self._stock_key(exchange, record_date)

            data = await redis.hgetall(key)
            if data:
                return [json.loads(v) for v in data.values()]
            return []
        except Exception as e:
            logger.error(f"Redis 종목 데이터 조회 실패: {e}")
            return []

    async def save_summary_record(
        self,
        exchange: str,
        record_date: date,
        summary: Dict[str, Any]
    ) -> bool:
        """요약 데이터 저장"""
        try:
            redis = await self._get_redis()
            key = self._summary_key(exchange, record_date)

            await redis.set(key, json.dumps(summary, default=str))
            await redis.expire(key, self.config.redis_ttl_seconds)

            logger.info(f"Redis에 요약 데이터 저장 완료: {exchange}/{record_date}")
            return True
        except Exception as e:
            logger.error(f"Redis 요약 데이터 저장 실패: {e}")
            return False

    async def get_summary_record(
        self,
        exchange: str,
        record_date: date
    ) -> Optional[Dict[str, Any]]:
        """요약 데이터 조회"""
        try:
            redis = await self._get_redis()
            key = self._summary_key(exchange, record_date)

            data = await redis.get(key)
            if data:
                return json.loads(data)
            return None
        except Exception as e:
            logger.error(f"Redis 요약 데이터 조회 실패: {e}")
            return None

    async def set_latest_date(self, exchange: str, record_date: date) -> bool:
        """최신 기록 날짜 설정"""
        try:
            redis = await self._get_redis()
            key = self._latest_key(exchange)

            await redis.set(key, format_date_for_db(record_date))
            return True
        except Exception as e:
            logger.error(f"Redis 최신 날짜 설정 실패: {e}")
            return False

    async def get_latest_date(self, exchange: str) -> Optional[date]:
        """최신 기록 날짜 조회"""
        try:
            redis = await self._get_redis()
            key = self._latest_key(exchange)

            data = await redis.get(key)
            if data:
                from app.utils.timezone_utils import parse_date_from_db
                return parse_date_from_db(data)
            return None
        except Exception as e:
            logger.error(f"Redis 최신 날짜 조회 실패: {e}")
            return None

    async def set_recording_status(self, status: Dict[str, Any]) -> bool:
        """기록 작업 상태 저장"""
        try:
            redis = await self._get_redis()
            await redis.hset(self.STATUS_KEY, mapping={k: json.dumps(v, default=str) for k, v in status.items()})
            return True
        except Exception as e:
            logger.error(f"Redis 기록 상태 저장 실패: {e}")
            return False

    async def get_recording_status(self) -> Dict[str, Any]:
        """기록 작업 상태 조회"""
        try:
            redis = await self._get_redis()
            data = await redis.hgetall(self.STATUS_KEY)
            if data:
                return {k: json.loads(v) for k, v in data.items()}
            return {}
        except Exception as e:
            logger.error(f"Redis 기록 상태 조회 실패: {e}")
            return {}

    async def clear_recording_status(self) -> bool:
        """기록 작업 상태 초기화"""
        try:
            redis = await self._get_redis()
            await redis.delete(self.STATUS_KEY)
            return True
        except Exception as e:
            logger.error(f"Redis 기록 상태 초기화 실패: {e}")
            return False


def get_redis_service() -> RedisService:
    """Redis 서비스 인스턴스 생성"""
    return RedisService()
