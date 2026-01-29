# -*- coding: utf-8 -*-
"""
Database Config
Redis/SQLite 연결 설정
"""
import os
import logging
import sqlite3
from functools import lru_cache
from typing import Optional

import aiosqlite
import redis.asyncio as redis

logger = logging.getLogger(__name__)


class DatabaseConfig:
    """데이터베이스 설정"""

    def __init__(self):
        self.project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

        # SQLite 설정
        self.sqlite_path = os.path.join(self.project_root, "data", "stock_history.db")

        # Redis 설정
        self.redis_host = os.getenv("REDIS_HOST", "localhost")
        self.redis_port = int(os.getenv("REDIS_PORT", 6379))
        self.redis_db = int(os.getenv("REDIS_DB", 0))
        self.redis_password = os.getenv("REDIS_PASSWORD", None)

        # Redis TTL 설정 (초 단위)
        self.redis_ttl_days = 7
        self.redis_ttl_seconds = self.redis_ttl_days * 24 * 60 * 60

    def ensure_data_directory(self):
        """데이터 디렉토리 생성"""
        data_dir = os.path.dirname(self.sqlite_path)
        if not os.path.exists(data_dir):
            os.makedirs(data_dir)
            logger.info(f"데이터 디렉토리 생성: {data_dir}")


# Redis 연결 풀
_redis_pool: Optional[redis.Redis] = None


async def get_redis_connection() -> redis.Redis:
    """Redis 연결 가져오기"""
    global _redis_pool

    if _redis_pool is None:
        config = get_database_config()
        _redis_pool = redis.Redis(
            host=config.redis_host,
            port=config.redis_port,
            db=config.redis_db,
            password=config.redis_password,
            decode_responses=True
        )
        logger.info(f"Redis 연결 생성: {config.redis_host}:{config.redis_port}")

    return _redis_pool


async def close_redis_connection():
    """Redis 연결 종료"""
    global _redis_pool

    if _redis_pool is not None:
        await _redis_pool.close()
        _redis_pool = None
        logger.info("Redis 연결 종료")


async def get_sqlite_connection() -> aiosqlite.Connection:
    """SQLite 비동기 연결 가져오기"""
    config = get_database_config()
    config.ensure_data_directory()

    conn = await aiosqlite.connect(config.sqlite_path)
    conn.row_factory = aiosqlite.Row
    return conn


def get_sqlite_sync_connection() -> sqlite3.Connection:
    """SQLite 동기 연결 가져오기 (초기화용)"""
    config = get_database_config()
    config.ensure_data_directory()

    conn = sqlite3.connect(config.sqlite_path)
    conn.row_factory = sqlite3.Row
    return conn


def init_sqlite_schema():
    """SQLite 스키마 초기화"""
    config = get_database_config()
    config.ensure_data_directory()

    conn = get_sqlite_sync_connection()
    cursor = conn.cursor()

    # daily_stock_records 테이블
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS daily_stock_records (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            record_date DATE NOT NULL,
            exchange VARCHAR(10) NOT NULL,
            currency VARCHAR(5) NOT NULL,
            ticker VARCHAR(20) NOT NULL,
            stock_name VARCHAR(100),
            quantity DECIMAL(20, 8),
            avg_purchase_price DECIMAL(20, 8),
            current_price DECIMAL(20, 8),
            purchase_amount DECIMAL(20, 8),
            eval_amount DECIMAL(20, 8),
            profit_loss_amount DECIMAL(20, 8),
            profit_loss_rate DECIMAL(10, 4),
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            UNIQUE(record_date, exchange, ticker)
        )
    """)

    # daily_summary_records 테이블
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS daily_summary_records (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            record_date DATE NOT NULL,
            exchange VARCHAR(10) NOT NULL,
            currency VARCHAR(5) NOT NULL,
            total_purchase_amount DECIMAL(20, 8),
            total_eval_amount DECIMAL(20, 8),
            total_profit_loss DECIMAL(20, 8),
            total_profit_rate DECIMAL(10, 4),
            stock_count INTEGER,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            UNIQUE(record_date, exchange)
        )
    """)

    # recording_logs 테이블
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS recording_logs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            record_date DATE NOT NULL,
            started_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            completed_at TIMESTAMP,
            status VARCHAR(20) NOT NULL DEFAULT 'STARTED',
            exchanges_processed TEXT,
            total_stocks INTEGER DEFAULT 0,
            error_message TEXT,
            UNIQUE(record_date)
        )
    """)

    # screening_results 테이블 (스크리닝 결과 - 필터별 점수 포함)
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS screening_results (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            screening_date DATE NOT NULL,
            ticker VARCHAR(20) NOT NULL,
            name VARCHAR(100),
            market VARCHAR(10) NOT NULL,
            current_price DECIMAL(20, 8),
            signal_strength VARCHAR(20),
            score INTEGER,
            price_above_cloud BOOLEAN,
            tenkan_above_kijun BOOLEAN,
            chikou_above_price BOOLEAN,
            cloud_bullish BOOLEAN,
            cloud_breakout BOOLEAN,
            golden_cross BOOLEAN,
            avg_trading_value DECIMAL(20, 8),

            -- 일목균형표 이격도
            ichimoku_disparity DECIMAL(10, 2),
            ichimoku_disparity_score INTEGER DEFAULT 0,

            -- 기술적 분석 점수
            bollinger_score INTEGER DEFAULT 0,
            ma_alignment_score INTEGER DEFAULT 0,
            cup_handle_score INTEGER DEFAULT 0,
            total_technical_score INTEGER DEFAULT 0,

            -- 펀더멘탈 분석 점수
            roe_score INTEGER DEFAULT 0,
            gpm_score INTEGER DEFAULT 0,
            debt_score INTEGER DEFAULT 0,
            capex_score INTEGER DEFAULT 0,
            total_fundamental_score INTEGER DEFAULT 0,

            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            UNIQUE(screening_date, ticker)
        )
    """)

    # asset_tags 테이블 (태그 정의)
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS asset_tags (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name VARCHAR(50) NOT NULL UNIQUE,
            category VARCHAR(30),
            color VARCHAR(7) DEFAULT '#6B7280',
            description TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)

    # stock_tags 테이블 (종목-태그 매핑)
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS stock_tags (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            ticker VARCHAR(20) NOT NULL,
            tag_id INTEGER NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            UNIQUE(ticker, tag_id),
            FOREIGN KEY (tag_id) REFERENCES asset_tags(id) ON DELETE CASCADE
        )
    """)

    # trade_records 테이블 (매매기록 자동 감지)
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS trade_records (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            trade_date DATE NOT NULL,
            exchange VARCHAR(10) NOT NULL,
            currency VARCHAR(5) NOT NULL,
            ticker VARCHAR(20) NOT NULL,
            stock_name VARCHAR(100),
            trade_type VARCHAR(20) NOT NULL,
            prev_quantity DECIMAL(20, 8),
            curr_quantity DECIMAL(20, 8),
            quantity_change DECIMAL(20, 8) NOT NULL,
            prev_price DECIMAL(20, 8),
            curr_price DECIMAL(20, 8),
            estimated_amount DECIMAL(20, 8),
            prev_record_date DATE,
            detection_method VARCHAR(20) DEFAULT 'AUTO',
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            UNIQUE(trade_date, exchange, ticker, trade_type)
        )
    """)

    # 인덱스 생성
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_stock_records_date ON daily_stock_records(record_date)")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_stock_records_ticker ON daily_stock_records(ticker)")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_stock_records_exchange ON daily_stock_records(exchange)")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_summary_records_date ON daily_summary_records(record_date)")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_recording_logs_date ON recording_logs(record_date)")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_screening_results_date ON screening_results(screening_date)")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_screening_results_ticker ON screening_results(ticker)")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_screening_results_market ON screening_results(market)")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_screening_results_score ON screening_results(score)")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_asset_tags_name ON asset_tags(name)")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_asset_tags_category ON asset_tags(category)")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_stock_tags_ticker ON stock_tags(ticker)")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_stock_tags_tag_id ON stock_tags(tag_id)")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_trade_records_date ON trade_records(trade_date)")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_trade_records_ticker ON trade_records(ticker)")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_trade_records_exchange ON trade_records(exchange)")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_trade_records_type ON trade_records(trade_type)")

    # 마이그레이션: screening_results에 필터별 점수 컬럼 추가 (기존 DB 호환)
    migration_columns = [
        ("bollinger_score", "INTEGER DEFAULT 0"),
        ("ma_alignment_score", "INTEGER DEFAULT 0"),
        ("cup_handle_score", "INTEGER DEFAULT 0"),
        ("total_technical_score", "INTEGER DEFAULT 0"),
        ("roe_score", "INTEGER DEFAULT 0"),
        ("gpm_score", "INTEGER DEFAULT 0"),
        ("debt_score", "INTEGER DEFAULT 0"),
        ("capex_score", "INTEGER DEFAULT 0"),
        ("total_fundamental_score", "INTEGER DEFAULT 0"),
        # 일목균형표 이격도
        ("ichimoku_disparity", "DECIMAL(10, 2)"),
        ("ichimoku_disparity_score", "INTEGER DEFAULT 0"),
    ]

    for col_name, col_type in migration_columns:
        try:
            cursor.execute(f"ALTER TABLE screening_results ADD COLUMN {col_name} {col_type}")
            logger.info(f"컬럼 추가: screening_results.{col_name}")
        except sqlite3.OperationalError:
            # 이미 존재하는 컬럼
            pass

    conn.commit()
    conn.close()

    logger.info(f"SQLite 스키마 초기화 완료: {config.sqlite_path}")


@lru_cache()
def get_database_config() -> DatabaseConfig:
    """데이터베이스 설정 싱글톤"""
    return DatabaseConfig()
