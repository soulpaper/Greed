# -*- coding: utf-8 -*-
"""
Tag Service
자산 태그 관리 서비스
"""
import logging
from typing import List, Optional, Tuple, Dict, Any
from functools import lru_cache

from app.config.database_config import get_sqlite_connection
from app.models.history_models import (
    AssetTagCreate,
    AssetTag,
    StockTagCreate,
    StockTag,
    StockWithTags,
    TagWithStocks,
)

logger = logging.getLogger(__name__)


class TagService:
    """자산 태그 관리 서비스"""

    # ============ 태그 CRUD ============

    async def create_tag(self, tag: AssetTagCreate) -> AssetTag:
        """태그 생성"""
        async with await get_sqlite_connection() as conn:
            cursor = await conn.execute(
                """
                INSERT INTO asset_tags (name, category, color, description)
                VALUES (?, ?, ?, ?)
                """,
                (tag.name, tag.category, tag.color, tag.description)
            )
            await conn.commit()

            tag_id = cursor.lastrowid
            return await self.get_tag_by_id(tag_id)

    async def get_tag_by_id(self, tag_id: int) -> Optional[AssetTag]:
        """ID로 태그 조회"""
        async with await get_sqlite_connection() as conn:
            cursor = await conn.execute(
                "SELECT * FROM asset_tags WHERE id = ?",
                (tag_id,)
            )
            row = await cursor.fetchone()

            if row:
                return AssetTag(
                    id=row["id"],
                    name=row["name"],
                    category=row["category"],
                    color=row["color"],
                    description=row["description"],
                    created_at=row["created_at"]
                )
            return None

    async def get_tag_by_name(self, name: str) -> Optional[AssetTag]:
        """이름으로 태그 조회"""
        async with await get_sqlite_connection() as conn:
            cursor = await conn.execute(
                "SELECT * FROM asset_tags WHERE name = ?",
                (name,)
            )
            row = await cursor.fetchone()

            if row:
                return AssetTag(
                    id=row["id"],
                    name=row["name"],
                    category=row["category"],
                    color=row["color"],
                    description=row["description"],
                    created_at=row["created_at"]
                )
            return None

    async def get_all_tags(
        self,
        category: Optional[str] = None,
        limit: int = 100,
        offset: int = 0
    ) -> Tuple[List[AssetTag], int]:
        """모든 태그 조회"""
        async with await get_sqlite_connection() as conn:
            # 총 개수 조회
            if category:
                count_cursor = await conn.execute(
                    "SELECT COUNT(*) FROM asset_tags WHERE category = ?",
                    (category,)
                )
            else:
                count_cursor = await conn.execute("SELECT COUNT(*) FROM asset_tags")

            total_count = (await count_cursor.fetchone())[0]

            # 태그 목록 조회
            if category:
                cursor = await conn.execute(
                    """
                    SELECT * FROM asset_tags
                    WHERE category = ?
                    ORDER BY category, name
                    LIMIT ? OFFSET ?
                    """,
                    (category, limit, offset)
                )
            else:
                cursor = await conn.execute(
                    """
                    SELECT * FROM asset_tags
                    ORDER BY category, name
                    LIMIT ? OFFSET ?
                    """,
                    (limit, offset)
                )

            rows = await cursor.fetchall()
            tags = [
                AssetTag(
                    id=row["id"],
                    name=row["name"],
                    category=row["category"],
                    color=row["color"],
                    description=row["description"],
                    created_at=row["created_at"]
                )
                for row in rows
            ]

            return tags, total_count

    async def update_tag(self, tag_id: int, tag: AssetTagCreate) -> Optional[AssetTag]:
        """태그 수정"""
        async with await get_sqlite_connection() as conn:
            await conn.execute(
                """
                UPDATE asset_tags
                SET name = ?, category = ?, color = ?, description = ?
                WHERE id = ?
                """,
                (tag.name, tag.category, tag.color, tag.description, tag_id)
            )
            await conn.commit()

            return await self.get_tag_by_id(tag_id)

    async def delete_tag(self, tag_id: int) -> bool:
        """태그 삭제 (연결된 종목 태그도 삭제됨)"""
        async with await get_sqlite_connection() as conn:
            cursor = await conn.execute(
                "DELETE FROM asset_tags WHERE id = ?",
                (tag_id,)
            )
            await conn.commit()

            return cursor.rowcount > 0

    # ============ 종목-태그 연결 관리 ============

    async def add_tag_to_stock(self, ticker: str, tag_id: int) -> bool:
        """종목에 태그 추가"""
        async with await get_sqlite_connection() as conn:
            try:
                await conn.execute(
                    """
                    INSERT OR IGNORE INTO stock_tags (ticker, tag_id)
                    VALUES (?, ?)
                    """,
                    (ticker.upper(), tag_id)
                )
                await conn.commit()
                return True
            except Exception as e:
                logger.error(f"종목 태그 추가 실패: {e}")
                return False

    async def remove_tag_from_stock(self, ticker: str, tag_id: int) -> bool:
        """종목에서 태그 제거"""
        async with await get_sqlite_connection() as conn:
            cursor = await conn.execute(
                """
                DELETE FROM stock_tags
                WHERE ticker = ? AND tag_id = ?
                """,
                (ticker.upper(), tag_id)
            )
            await conn.commit()

            return cursor.rowcount > 0

    async def bulk_add_tags(self, tickers: List[str], tag_ids: List[int]) -> Dict[str, Any]:
        """여러 종목에 여러 태그 일괄 추가"""
        async with await get_sqlite_connection() as conn:
            success_count = 0
            for ticker in tickers:
                for tag_id in tag_ids:
                    try:
                        await conn.execute(
                            """
                            INSERT OR IGNORE INTO stock_tags (ticker, tag_id)
                            VALUES (?, ?)
                            """,
                            (ticker.upper(), tag_id)
                        )
                        success_count += 1
                    except Exception as e:
                        logger.warning(f"태그 추가 실패 ({ticker}, {tag_id}): {e}")

            await conn.commit()

            return {
                "success": True,
                "total_assignments": len(tickers) * len(tag_ids),
                "successful": success_count
            }

    async def get_tags_for_stock(self, ticker: str) -> List[AssetTag]:
        """종목의 모든 태그 조회"""
        async with await get_sqlite_connection() as conn:
            cursor = await conn.execute(
                """
                SELECT t.* FROM asset_tags t
                JOIN stock_tags st ON t.id = st.tag_id
                WHERE st.ticker = ?
                ORDER BY t.category, t.name
                """,
                (ticker.upper(),)
            )
            rows = await cursor.fetchall()

            return [
                AssetTag(
                    id=row["id"],
                    name=row["name"],
                    category=row["category"],
                    color=row["color"],
                    description=row["description"],
                    created_at=row["created_at"]
                )
                for row in rows
            ]

    async def get_stocks_by_tag(
        self,
        tag_id: int,
        limit: int = 100,
        offset: int = 0
    ) -> Tuple[List[str], int]:
        """태그에 연결된 종목 목록 조회"""
        async with await get_sqlite_connection() as conn:
            # 총 개수
            count_cursor = await conn.execute(
                "SELECT COUNT(*) FROM stock_tags WHERE tag_id = ?",
                (tag_id,)
            )
            total_count = (await count_cursor.fetchone())[0]

            # 종목 목록
            cursor = await conn.execute(
                """
                SELECT ticker FROM stock_tags
                WHERE tag_id = ?
                ORDER BY ticker
                LIMIT ? OFFSET ?
                """,
                (tag_id, limit, offset)
            )
            rows = await cursor.fetchall()
            tickers = [row["ticker"] for row in rows]

            return tickers, total_count

    async def get_stocks_by_tags(
        self,
        tag_ids: List[int],
        match_all: bool = False
    ) -> List[str]:
        """
        여러 태그로 종목 검색

        Args:
            tag_ids: 태그 ID 목록
            match_all: True면 모든 태그를 가진 종목만, False면 하나라도 가진 종목
        """
        if not tag_ids:
            return []

        async with await get_sqlite_connection() as conn:
            placeholders = ",".join(["?" for _ in tag_ids])

            if match_all:
                # 모든 태그를 가진 종목
                cursor = await conn.execute(
                    f"""
                    SELECT ticker FROM stock_tags
                    WHERE tag_id IN ({placeholders})
                    GROUP BY ticker
                    HAVING COUNT(DISTINCT tag_id) = ?
                    ORDER BY ticker
                    """,
                    (*tag_ids, len(tag_ids))
                )
            else:
                # 하나라도 가진 종목
                cursor = await conn.execute(
                    f"""
                    SELECT DISTINCT ticker FROM stock_tags
                    WHERE tag_id IN ({placeholders})
                    ORDER BY ticker
                    """,
                    tag_ids
                )

            rows = await cursor.fetchall()
            return [row["ticker"] for row in rows]

    async def get_stocks_with_tags(
        self,
        tickers: Optional[List[str]] = None,
        tag_ids: Optional[List[int]] = None,
        limit: int = 100,
        offset: int = 0
    ) -> Tuple[List[StockWithTags], int]:
        """종목 목록과 각 종목의 태그 정보 조회"""
        async with await get_sqlite_connection() as conn:
            # 종목 목록 결정
            if tickers:
                target_tickers = [t.upper() for t in tickers]
            elif tag_ids:
                target_tickers = await self.get_stocks_by_tags(tag_ids, match_all=False)
            else:
                # 태그가 있는 모든 종목
                cursor = await conn.execute(
                    "SELECT DISTINCT ticker FROM stock_tags ORDER BY ticker"
                )
                rows = await cursor.fetchall()
                target_tickers = [row["ticker"] for row in rows]

            total_count = len(target_tickers)
            paginated_tickers = target_tickers[offset:offset + limit]

            # 각 종목의 태그 정보 조회
            result = []
            for ticker in paginated_tickers:
                # 최신 종목 정보 조회
                stock_cursor = await conn.execute(
                    """
                    SELECT ticker, stock_name, exchange
                    FROM daily_stock_records
                    WHERE ticker = ?
                    ORDER BY record_date DESC
                    LIMIT 1
                    """,
                    (ticker,)
                )
                stock_row = await stock_cursor.fetchone()

                tags = await self.get_tags_for_stock(ticker)

                result.append(StockWithTags(
                    ticker=ticker,
                    stock_name=stock_row["stock_name"] if stock_row else None,
                    exchange=stock_row["exchange"] if stock_row else None,
                    tags=tags
                ))

            return result, total_count

    async def get_tag_statistics(self) -> List[TagWithStocks]:
        """모든 태그와 각 태그의 종목 수 통계"""
        async with await get_sqlite_connection() as conn:
            cursor = await conn.execute(
                """
                SELECT t.*, COUNT(st.ticker) as stock_count
                FROM asset_tags t
                LEFT JOIN stock_tags st ON t.id = st.tag_id
                GROUP BY t.id
                ORDER BY stock_count DESC, t.name
                """
            )
            rows = await cursor.fetchall()

            result = []
            for row in rows:
                tag = AssetTag(
                    id=row["id"],
                    name=row["name"],
                    category=row["category"],
                    color=row["color"],
                    description=row["description"],
                    created_at=row["created_at"]
                )

                # 종목 목록 조회
                tickers, _ = await self.get_stocks_by_tag(tag.id, limit=1000)

                result.append(TagWithStocks(
                    tag=tag,
                    tickers=tickers,
                    stock_count=row["stock_count"]
                ))

            return result

    async def get_categories(self) -> List[str]:
        """모든 태그 카테고리 목록 조회"""
        async with await get_sqlite_connection() as conn:
            cursor = await conn.execute(
                """
                SELECT DISTINCT category FROM asset_tags
                WHERE category IS NOT NULL
                ORDER BY category
                """
            )
            rows = await cursor.fetchall()
            return [row["category"] for row in rows]


# 서비스 인스턴스 싱글톤
_tag_service: Optional[TagService] = None


def get_tag_service() -> TagService:
    """TagService 싱글톤 인스턴스 반환"""
    global _tag_service

    if _tag_service is None:
        _tag_service = TagService()

    return _tag_service
