# -*- coding: utf-8 -*-
"""
Tag Controller
자산 태그 관리 API 엔드포인트
"""
import logging
from typing import Optional, List

from fastapi import APIRouter, HTTPException, Query, Depends

from app.models.history_models import (
    AssetTagCreate,
    AssetTag,
    TagListResponse,
    StocksByTagResponse,
    StockWithTags,
    BulkTagAssignRequest,
    TagWithStocks,
)
from app.services.tag_service import get_tag_service, TagService

logger = logging.getLogger(__name__)

router = APIRouter(
    prefix="/api/v1/tags",
    tags=["tags"],
    responses={404: {"description": "Not found"}}
)


# ============ 태그 CRUD ============

@router.post("", response_model=AssetTag)
async def create_tag(
    tag: AssetTagCreate,
    service: TagService = Depends(get_tag_service)
):
    """
    새 태그 생성

    자산 분류를 위한 새로운 태그를 생성합니다.

    - **name**: 태그 이름 (필수, 고유)
    - **category**: 태그 카테고리 (자산종류, 전략, 섹터 등)
    - **color**: 태그 색상 (HEX, 예: #FF5733)
    - **description**: 태그 설명
    """
    try:
        # 이름 중복 체크
        existing = await service.get_tag_by_name(tag.name)
        if existing:
            raise HTTPException(status_code=400, detail=f"태그 '{tag.name}'이(가) 이미 존재합니다.")

        result = await service.create_tag(tag)
        logger.info(f"태그 생성 완료: {tag.name}")
        return result
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"태그 생성 실패: {str(e)}")
        raise HTTPException(status_code=500, detail=f"태그 생성 중 오류 발생: {str(e)}")


@router.get("", response_model=TagListResponse)
async def get_tags(
    category: Optional[str] = Query(None, description="태그 카테고리 필터"),
    limit: int = Query(100, le=1000, description="조회 개수"),
    offset: int = Query(0, ge=0, description="시작 위치"),
    service: TagService = Depends(get_tag_service)
):
    """
    태그 목록 조회

    모든 태그 또는 특정 카테고리의 태그 목록을 조회합니다.
    """
    try:
        tags, total_count = await service.get_all_tags(
            category=category,
            limit=limit,
            offset=offset
        )

        return TagListResponse(
            tags=tags,
            total_count=total_count
        )
    except Exception as e:
        logger.error(f"태그 목록 조회 실패: {str(e)}")
        raise HTTPException(status_code=500, detail=f"조회 중 오류 발생: {str(e)}")


@router.get("/categories")
async def get_categories(
    service: TagService = Depends(get_tag_service)
):
    """
    태그 카테고리 목록 조회

    사용 중인 모든 태그 카테고리를 조회합니다.
    """
    try:
        categories = await service.get_categories()
        return {"categories": categories}
    except Exception as e:
        logger.error(f"카테고리 목록 조회 실패: {str(e)}")
        raise HTTPException(status_code=500, detail=f"조회 중 오류 발생: {str(e)}")


@router.get("/statistics")
async def get_tag_statistics(
    service: TagService = Depends(get_tag_service)
):
    """
    태그 통계 조회

    모든 태그와 각 태그에 연결된 종목 수를 조회합니다.
    """
    try:
        stats = await service.get_tag_statistics()
        return {
            "statistics": [
                {
                    "tag": stat.tag,
                    "stock_count": stat.stock_count,
                    "tickers": stat.tickers
                }
                for stat in stats
            ]
        }
    except Exception as e:
        logger.error(f"태그 통계 조회 실패: {str(e)}")
        raise HTTPException(status_code=500, detail=f"조회 중 오류 발생: {str(e)}")


@router.get("/{tag_id}", response_model=AssetTag)
async def get_tag(
    tag_id: int,
    service: TagService = Depends(get_tag_service)
):
    """
    특정 태그 조회

    태그 ID로 태그 정보를 조회합니다.
    """
    try:
        tag = await service.get_tag_by_id(tag_id)
        if not tag:
            raise HTTPException(status_code=404, detail=f"태그 ID {tag_id}을(를) 찾을 수 없습니다.")
        return tag
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"태그 조회 실패: {str(e)}")
        raise HTTPException(status_code=500, detail=f"조회 중 오류 발생: {str(e)}")


@router.put("/{tag_id}", response_model=AssetTag)
async def update_tag(
    tag_id: int,
    tag: AssetTagCreate,
    service: TagService = Depends(get_tag_service)
):
    """
    태그 수정

    기존 태그의 정보를 수정합니다.
    """
    try:
        existing = await service.get_tag_by_id(tag_id)
        if not existing:
            raise HTTPException(status_code=404, detail=f"태그 ID {tag_id}을(를) 찾을 수 없습니다.")

        # 이름 변경 시 중복 체크
        if tag.name != existing.name:
            name_exists = await service.get_tag_by_name(tag.name)
            if name_exists:
                raise HTTPException(status_code=400, detail=f"태그 '{tag.name}'이(가) 이미 존재합니다.")

        result = await service.update_tag(tag_id, tag)
        logger.info(f"태그 수정 완료: {tag_id}")
        return result
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"태그 수정 실패: {str(e)}")
        raise HTTPException(status_code=500, detail=f"수정 중 오류 발생: {str(e)}")


@router.delete("/{tag_id}")
async def delete_tag(
    tag_id: int,
    service: TagService = Depends(get_tag_service)
):
    """
    태그 삭제

    태그를 삭제합니다. 연결된 종목-태그 관계도 함께 삭제됩니다.
    """
    try:
        existing = await service.get_tag_by_id(tag_id)
        if not existing:
            raise HTTPException(status_code=404, detail=f"태그 ID {tag_id}을(를) 찾을 수 없습니다.")

        success = await service.delete_tag(tag_id)
        if success:
            logger.info(f"태그 삭제 완료: {tag_id}")
            return {"success": True, "message": f"태그 '{existing.name}'이(가) 삭제되었습니다."}
        else:
            raise HTTPException(status_code=500, detail="태그 삭제에 실패했습니다.")
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"태그 삭제 실패: {str(e)}")
        raise HTTPException(status_code=500, detail=f"삭제 중 오류 발생: {str(e)}")


# ============ 종목-태그 연결 관리 ============

@router.get("/{tag_id}/stocks", response_model=StocksByTagResponse)
async def get_stocks_by_tag(
    tag_id: int,
    limit: int = Query(100, le=1000, description="조회 개수"),
    offset: int = Query(0, ge=0, description="시작 위치"),
    service: TagService = Depends(get_tag_service)
):
    """
    태그에 연결된 종목 목록 조회

    특정 태그가 부여된 모든 종목을 조회합니다.
    """
    try:
        tag = await service.get_tag_by_id(tag_id)
        if not tag:
            raise HTTPException(status_code=404, detail=f"태그 ID {tag_id}을(를) 찾을 수 없습니다.")

        tickers, total_count = await service.get_stocks_by_tag(tag_id, limit, offset)

        # 종목 정보와 태그 조회
        stocks, _ = await service.get_stocks_with_tags(tickers=tickers)

        return StocksByTagResponse(
            tag=tag,
            stocks=stocks,
            total_count=total_count
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"태그별 종목 조회 실패: {str(e)}")
        raise HTTPException(status_code=500, detail=f"조회 중 오류 발생: {str(e)}")


@router.post("/{tag_id}/stocks/{ticker}")
async def add_tag_to_stock(
    tag_id: int,
    ticker: str,
    service: TagService = Depends(get_tag_service)
):
    """
    종목에 태그 추가

    특정 종목에 태그를 부여합니다.
    """
    try:
        tag = await service.get_tag_by_id(tag_id)
        if not tag:
            raise HTTPException(status_code=404, detail=f"태그 ID {tag_id}을(를) 찾을 수 없습니다.")

        success = await service.add_tag_to_stock(ticker, tag_id)
        if success:
            logger.info(f"종목 태그 추가: {ticker} <- {tag.name}")
            return {
                "success": True,
                "message": f"종목 '{ticker}'에 태그 '{tag.name}'이(가) 추가되었습니다."
            }
        else:
            raise HTTPException(status_code=500, detail="태그 추가에 실패했습니다.")
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"종목 태그 추가 실패: {str(e)}")
        raise HTTPException(status_code=500, detail=f"추가 중 오류 발생: {str(e)}")


@router.delete("/{tag_id}/stocks/{ticker}")
async def remove_tag_from_stock(
    tag_id: int,
    ticker: str,
    service: TagService = Depends(get_tag_service)
):
    """
    종목에서 태그 제거

    특정 종목에서 태그를 제거합니다.
    """
    try:
        tag = await service.get_tag_by_id(tag_id)
        if not tag:
            raise HTTPException(status_code=404, detail=f"태그 ID {tag_id}을(를) 찾을 수 없습니다.")

        success = await service.remove_tag_from_stock(ticker, tag_id)
        if success:
            logger.info(f"종목 태그 제거: {ticker} -x- {tag.name}")
            return {
                "success": True,
                "message": f"종목 '{ticker}'에서 태그 '{tag.name}'이(가) 제거되었습니다."
            }
        else:
            raise HTTPException(status_code=404, detail=f"종목 '{ticker}'에 태그 '{tag.name}'이(가) 없습니다.")
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"종목 태그 제거 실패: {str(e)}")
        raise HTTPException(status_code=500, detail=f"제거 중 오류 발생: {str(e)}")


@router.post("/bulk-assign")
async def bulk_assign_tags(
    request: BulkTagAssignRequest,
    service: TagService = Depends(get_tag_service)
):
    """
    태그 일괄 할당

    여러 종목에 여러 태그를 한 번에 할당합니다.
    """
    try:
        result = await service.bulk_add_tags(request.tickers, request.tag_ids)
        logger.info(f"태그 일괄 할당: {len(request.tickers)}개 종목, {len(request.tag_ids)}개 태그")
        return result
    except Exception as e:
        logger.error(f"태그 일괄 할당 실패: {str(e)}")
        raise HTTPException(status_code=500, detail=f"할당 중 오류 발생: {str(e)}")


# ============ 종목별 태그 조회 ============

@router.get("/stocks/{ticker}/tags")
async def get_stock_tags(
    ticker: str,
    service: TagService = Depends(get_tag_service)
):
    """
    종목의 태그 조회

    특정 종목에 부여된 모든 태그를 조회합니다.
    """
    try:
        tags = await service.get_tags_for_stock(ticker)
        return {
            "ticker": ticker.upper(),
            "tags": tags,
            "count": len(tags)
        }
    except Exception as e:
        logger.error(f"종목 태그 조회 실패: {str(e)}")
        raise HTTPException(status_code=500, detail=f"조회 중 오류 발생: {str(e)}")


@router.get("/stocks/search")
async def search_stocks_by_tags(
    tag_ids: List[int] = Query(..., description="태그 ID 목록"),
    match_all: bool = Query(False, description="모든 태그 일치 여부 (True: AND, False: OR)"),
    limit: int = Query(100, le=1000, description="조회 개수"),
    offset: int = Query(0, ge=0, description="시작 위치"),
    service: TagService = Depends(get_tag_service)
):
    """
    태그로 종목 검색

    지정한 태그를 가진 종목을 검색합니다.

    - **match_all=False**: 태그 중 하나라도 가진 종목 (OR 조건)
    - **match_all=True**: 모든 태그를 가진 종목 (AND 조건)
    """
    try:
        tickers = await service.get_stocks_by_tags(tag_ids, match_all)
        total_count = len(tickers)
        paginated_tickers = tickers[offset:offset + limit]

        # 종목 정보와 태그 조회
        stocks, _ = await service.get_stocks_with_tags(tickers=paginated_tickers)

        return {
            "stocks": stocks,
            "total_count": total_count,
            "limit": limit,
            "offset": offset,
            "match_all": match_all,
            "tag_ids": tag_ids
        }
    except Exception as e:
        logger.error(f"태그 검색 실패: {str(e)}")
        raise HTTPException(status_code=500, detail=f"검색 중 오류 발생: {str(e)}")
