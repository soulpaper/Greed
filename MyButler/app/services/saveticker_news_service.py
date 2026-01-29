"""
SaveTicker 뉴스 파싱 서비스

https://api.saveticker.com API를 통해 뉴스를 가져옵니다.

의존성:
    pip install aiohttp  # 비동기 HTTP 클라이언트 (선택)
    # 또는 기본 urllib만 사용 가능
"""

import json
import logging
import urllib.request
import urllib.parse
from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional
from enum import Enum

logger = logging.getLogger(__name__)


class NewsSource(str, Enum):
    """뉴스 소스"""
    FIVELINES = "fivelines_news"  # 세이브티커 자체 뉴스
    FINANCIAL_JUICE = "financial-juice"  # 파이낸셜 주스
    REUTERS = "reuters"  # 로이터


class SortOrder(str, Enum):
    """정렬 순서"""
    NEWEST = "created_at_desc"
    OLDEST = "created_at_asc"
    MOST_VIEWED = "view_count_desc"


@dataclass
class Ticker:
    """티커(주식 심볼) 정보"""
    symbol: str
    name: str = ""
    exchange: str = ""

    def to_dict(self) -> dict:
        return {
            "symbol": self.symbol,
            "name": self.name,
            "exchange": self.exchange,
        }


@dataclass
class NewsItem:
    """뉴스 아이템"""
    id: str
    title: str
    content: str
    source: str
    created_at: datetime
    url: str = ""
    thumbnail: str = ""
    view_count: int = 0
    comment_count: int = 0
    tags: list[str] = field(default_factory=list)
    tickers: list[Ticker] = field(default_factory=list)
    author_name: str = ""
    original_title: str = ""  # 원본 영문 제목

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "title": self.title,
            "content": self.content,
            "source": self.source,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "url": self.url,
            "thumbnail": self.thumbnail,
            "view_count": self.view_count,
            "comment_count": self.comment_count,
            "tags": self.tags,
            "tickers": [t.to_dict() for t in self.tickers],
            "author_name": self.author_name,
            "original_title": self.original_title,
        }


class SaveTickerNewsService:
    """SaveTicker 뉴스 API 서비스"""

    BASE_URL = "https://api.saveticker.com/api"

    def __init__(self, timeout: int = 30):
        """
        Args:
            timeout: HTTP 요청 타임아웃 (초)
        """
        self.timeout = timeout

    def _make_request(self, endpoint: str, params: dict = None) -> dict:
        """API 요청 수행"""
        url = f"{self.BASE_URL}/{endpoint}"
        if params:
            url += "?" + urllib.parse.urlencode(params)

        logger.debug(f"API 요청: {url}")

        req = urllib.request.Request(
            url,
            headers={
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
                "Accept": "application/json",
                "Referer": "https://www.saveticker.com/",
            }
        )

        with urllib.request.urlopen(req, timeout=self.timeout) as response:
            data = json.loads(response.read().decode("utf-8"))
            return data

    def fetch_news(
        self,
        page: int = 1,
        page_size: int = 20,
        sort: SortOrder = SortOrder.NEWEST,
        sources: list[NewsSource] = None,
        tag: str = None,
    ) -> tuple[list[NewsItem], int]:
        """
        뉴스 목록을 가져옵니다.

        Args:
            page: 페이지 번호 (1부터 시작)
            page_size: 페이지당 뉴스 개수 (최대 50)
            sort: 정렬 순서
            sources: 뉴스 소스 필터 (None이면 전체)
            tag: 태그 필터

        Returns:
            (뉴스 목록, 전체 개수) 튜플
        """
        params = {
            "page": page,
            "page_size": min(page_size, 50),
            "sort": sort.value,
        }

        if sources:
            params["sources"] = ",".join(s.value for s in sources)
        else:
            # 기본: 모든 소스
            params["sources"] = ",".join(s.value for s in NewsSource)

        if tag:
            params["tag"] = tag

        try:
            data = self._make_request("news/list", params)
            news_list = data.get("news_list", [])
            total_count = data.get("total_count", 0)

            items = [self._parse_news_item(item) for item in news_list]
            logger.info(f"{len(items)}개 뉴스 가져옴 (전체: {total_count}개)")

            return items, total_count

        except Exception as e:
            logger.error(f"뉴스 가져오기 실패: {e}")
            raise

    def fetch_all_news(
        self,
        max_items: int = 100,
        sort: SortOrder = SortOrder.NEWEST,
        sources: list[NewsSource] = None,
    ) -> list[NewsItem]:
        """
        여러 페이지의 뉴스를 가져옵니다.

        Args:
            max_items: 가져올 최대 뉴스 개수
            sort: 정렬 순서
            sources: 뉴스 소스 필터

        Returns:
            뉴스 목록
        """
        all_items = []
        page = 1
        page_size = 50

        while len(all_items) < max_items:
            items, total = self.fetch_news(
                page=page,
                page_size=page_size,
                sort=sort,
                sources=sources,
            )

            if not items:
                break

            all_items.extend(items)
            page += 1

            if len(all_items) >= total:
                break

        return all_items[:max_items]

    def fetch_tags(self) -> list[dict]:
        """
        사용 가능한 태그 목록을 가져옵니다.

        Returns:
            태그 목록
        """
        try:
            data = self._make_request("tags/list")
            return data.get("tags", [])
        except Exception as e:
            logger.error(f"태그 목록 가져오기 실패: {e}")
            raise

    def _parse_news_item(self, data: dict) -> NewsItem:
        """API 응답을 NewsItem으로 변환"""
        # 생성 시간 파싱
        created_at = None
        if data.get("created_at"):
            try:
                created_at = datetime.fromisoformat(
                    data["created_at"].replace("Z", "+00:00")
                )
            except ValueError:
                pass

        # 티커 정보 파싱
        tickers = []
        for ticker_data in data.get("tickers", []) or []:
            tickers.append(Ticker(
                symbol=ticker_data.get("symbol", ""),
                name=ticker_data.get("name", ""),
                exchange=ticker_data.get("exchange", ""),
            ))

        # 번역된 제목/내용 (한글 우선)
        translations = data.get("translations", {}) or {}
        ko_trans = translations.get("ko", {}) or {}

        title = ko_trans.get("title") or data.get("title", "")
        content = ko_trans.get("content") or data.get("content", "")

        return NewsItem(
            id=str(data.get("id", "")),
            title=title,
            content=content,
            source=data.get("source", ""),
            created_at=created_at,
            url=f"https://www.saveticker.com/news/{data.get('id', '')}",
            thumbnail=data.get("thumbnail", "") or "",
            view_count=data.get("view_count", 0) or 0,
            comment_count=data.get("comment_count", 0) or 0,
            tags=data.get("tag_names", []) or [],
            tickers=tickers,
            author_name=data.get("author_name", "") or "",
            original_title=data.get("title", ""),
        )


# 편의 함수
def fetch_news(
    page: int = 1,
    page_size: int = 20,
    sort: str = "newest",
    sources: list[str] = None,
) -> list[dict]:
    """
    뉴스를 가져옵니다 (간편 함수).

    Args:
        page: 페이지 번호
        page_size: 페이지당 개수
        sort: 정렬 ("newest", "oldest", "most_viewed")
        sources: 소스 필터 ("fivelines", "financial-juice", "reuters")

    Returns:
        뉴스 딕셔너리 리스트
    """
    service = SaveTickerNewsService()

    # 정렬 변환
    sort_map = {
        "newest": SortOrder.NEWEST,
        "oldest": SortOrder.OLDEST,
        "most_viewed": SortOrder.MOST_VIEWED,
    }
    sort_order = sort_map.get(sort, SortOrder.NEWEST)

    # 소스 변환
    source_list = None
    if sources:
        source_map = {
            "fivelines": NewsSource.FIVELINES,
            "financial-juice": NewsSource.FINANCIAL_JUICE,
            "reuters": NewsSource.REUTERS,
        }
        source_list = [source_map[s] for s in sources if s in source_map]

    items, _ = service.fetch_news(
        page=page,
        page_size=page_size,
        sort=sort_order,
        sources=source_list,
    )

    return [item.to_dict() for item in items]


def fetch_latest_news(count: int = 10) -> list[dict]:
    """
    최신 뉴스를 가져옵니다.

    Args:
        count: 가져올 뉴스 개수

    Returns:
        뉴스 딕셔너리 리스트
    """
    return fetch_news(page=1, page_size=count, sort="newest")


# 사용 예시
if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)

    print("SaveTicker 뉴스 가져오는 중...\n")

    service = SaveTickerNewsService()

    # 최신 뉴스 10개 가져오기
    news_items, total = service.fetch_news(page=1, page_size=10)

    print(f"전체 뉴스 수: {total:,}개")
    print(f"가져온 뉴스: {len(news_items)}개\n")
    print("=" * 60)

    for i, news in enumerate(news_items, 1):
        print(f"\n[{i}] {news.title}")
        print(f"    소스: {news.source}")
        print(f"    시간: {news.created_at}")
        print(f"    조회수: {news.view_count:,}")
        if news.tickers:
            tickers_str = ", ".join(f"${t.symbol}" for t in news.tickers)
            print(f"    티커: {tickers_str}")
        if news.tags:
            print(f"    태그: {', '.join(news.tags)}")
        print(f"    URL: {news.url}")
