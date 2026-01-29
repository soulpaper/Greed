# -*- coding: utf-8 -*-
"""
Screening Controller
주식 스크리닝 API 엔드포인트
"""
import logging
from datetime import date
from typing import Optional, List

from fastapi import APIRouter, HTTPException, Query, Depends, BackgroundTasks

from app.models.screening_models import (
    ScreeningRequest,
    ScreeningResponse,
    ScreeningHistoryResponse,
    MarketType,
    CombineMode,
)
from app.services.screening_service import get_screening_service, ScreeningService

logger = logging.getLogger(__name__)

router = APIRouter(
    prefix="/api/v1/screening",
    tags=["screening"],
    responses={404: {"description": "Not found"}}
)


@router.post("/run", response_model=ScreeningResponse)
async def run_screening(
    request: ScreeningRequest = None,
    service: ScreeningService = Depends(get_screening_service)
):
    """
    통합 주식 스크리닝 실행

    거래대금 조건과 선택한 필터 조건을 충족하는 종목을 찾습니다.

    - **market**: US (미국), KR (한국), ALL (전체)
    - **min_score**: 최소 점수 (기본 50)
    - **perfect_only**: 완벽 조건만 (일목균형표: 주가>구름 + 전환선>기준선 + 후행스팬>26일전주가)
    - **limit**: 결과 개수
    - **filters**: 적용할 필터 목록 (ichimoku, bollinger, ma_alignment, cup_handle)
    - **combine_mode**: 필터 조합 모드 (any: OR, all: AND)
    """
    try:
        if request is None:
            request = ScreeningRequest()

        logger.info(f"스크리닝 요청: market={request.market}, filters={request.filters}, combine_mode={request.combine_mode}")

        result = service.run_screening(
            market=request.market,
            min_score=request.min_score,
            perfect_only=request.perfect_only,
            limit=request.limit,
            filters=request.filters,
            combine_mode=request.combine_mode.value
        )

        return result

    except Exception as e:
        logger.error(f"스크리닝 실행 실패: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"스크리닝 중 오류 발생: {str(e)}")


@router.get("/us")
async def screen_us_stocks(
    min_score: int = Query(default=50, ge=-100, le=100, description="최소 점수"),
    perfect_only: bool = Query(default=False, description="완벽 조건만"),
    limit: int = Query(default=20, le=100, description="결과 개수"),
    filters: List[str] = Query(default=["ichimoku"], description="적용할 필터 목록"),
    combine_mode: CombineMode = Query(default=CombineMode.ANY, description="필터 조합 모드"),
    service: ScreeningService = Depends(get_screening_service)
):
    """
    미국 주식 스크리닝

    거래대금 $20M 이상 + 선택한 필터 조건
    """
    try:
        result = service.run_screening(
            market=MarketType.US,
            min_score=min_score,
            perfect_only=perfect_only,
            limit=limit,
            filters=filters,
            combine_mode=combine_mode.value
        )

        return result

    except Exception as e:
        logger.error(f"미국 주식 스크리닝 실패: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"스크리닝 중 오류 발생: {str(e)}")


@router.get("/kr")
async def screen_kr_stocks(
    min_score: int = Query(default=50, ge=-100, le=100, description="최소 점수"),
    perfect_only: bool = Query(default=False, description="완벽 조건만"),
    limit: int = Query(default=20, le=100, description="결과 개수"),
    filters: List[str] = Query(default=["ichimoku"], description="적용할 필터 목록"),
    combine_mode: CombineMode = Query(default=CombineMode.ANY, description="필터 조합 모드"),
    service: ScreeningService = Depends(get_screening_service)
):
    """
    한국 주식 스크리닝

    거래대금 50억원 이상 + 선택한 필터 조건
    """
    try:
        result = service.run_screening(
            market=MarketType.KR,
            min_score=min_score,
            perfect_only=perfect_only,
            limit=limit,
            filters=filters,
            combine_mode=combine_mode.value
        )

        return result

    except Exception as e:
        logger.error(f"한국 주식 스크리닝 실패: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"스크리닝 중 오류 발생: {str(e)}")


@router.get("/perfect")
async def get_perfect_signals(
    market: MarketType = Query(default=MarketType.ALL, description="대상 시장"),
    limit: int = Query(default=20, le=100, description="결과 개수"),
    service: ScreeningService = Depends(get_screening_service)
):
    """
    완벽 조건 충족 종목 조회 (일목균형표)

    - 주가 > 구름대
    - 전환선 > 기준선
    - 후행스팬 > 26일 전 주가
    """
    try:
        result = service.run_screening(
            market=market,
            min_score=0,  # 점수 무관, 조건만 체크
            perfect_only=True,
            limit=limit,
            filters=["ichimoku"]
        )

        return result

    except Exception as e:
        logger.error(f"완벽 조건 스크리닝 실패: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"스크리닝 중 오류 발생: {str(e)}")


# ============= 새로운 기술적 분석 전용 엔드포인트 =============


@router.get("/bollinger-squeeze", response_model=ScreeningResponse)
async def screen_bollinger_squeeze(
    market: MarketType = Query(default=MarketType.ALL, description="대상 시장"),
    min_score: int = Query(default=40, ge=0, le=100, description="최소 점수"),
    limit: int = Query(default=20, le=100, description="결과 개수"),
    service: ScreeningService = Depends(get_screening_service)
):
    """
    볼린저 밴드 스퀴즈 스크리닝 (에너지 응축형)

    밴드폭이 좁아진 상태(스퀴즈)에서 거래량이 증가하는 종목을 찾습니다.

    **신호 조건:**
    - 스퀴즈 (BandWidth 하위 20%): +25점
    - 강한 스퀴즈 (하위 10%): +35점
    - 거래량 2배 이상 급증: +20점 / 3배 이상: +30점
    - 밴드 상단 돌파 시도 (%B >= 0.8): +15점

    **최대 점수:** 80점
    """
    try:
        result = service.run_bollinger_screening(
            market=market,
            min_score=min_score,
            limit=limit
        )
        return result

    except Exception as e:
        logger.error(f"볼린저 스퀴즈 스크리닝 실패: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"스크리닝 중 오류 발생: {str(e)}")


@router.get("/ma-alignment", response_model=ScreeningResponse)
async def screen_ma_alignment(
    market: MarketType = Query(default=MarketType.ALL, description="대상 시장"),
    min_score: int = Query(default=40, ge=0, le=100, description="최소 점수"),
    limit: int = Query(default=20, le=100, description="결과 개수"),
    service: ScreeningService = Depends(get_screening_service)
):
    """
    이동평균선 정배열 스크리닝 (추세 확정형)

    이동평균선이 정배열 상태이고 골든크로스가 발생한 종목을 찾습니다.

    **신호 조건:**
    - 완전 정배열 (Price > 5 > 20 > 60 > 120): +40점
    - 부분 정배열 (3단계): +25점
    - 단기 골든크로스 (5/20): +10점
    - 중기 골든크로스 (20/60): +15점
    - 장기 골든크로스 (60/120): +20점
    - 이격도 적정 (5~15%): +10점
    - 이격도 과열 (>15%): -20점

    **최대 점수:** 95점
    """
    try:
        result = service.run_ma_alignment_screening(
            market=market,
            min_score=min_score,
            limit=limit
        )
        return result

    except Exception as e:
        logger.error(f"이평선 정배열 스크리닝 실패: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"스크리닝 중 오류 발생: {str(e)}")


@router.get("/cup-and-handle", response_model=ScreeningResponse)
async def screen_cup_and_handle(
    market: MarketType = Query(default=MarketType.ALL, description="대상 시장"),
    min_score: int = Query(default=40, ge=0, le=100, description="최소 점수"),
    limit: int = Query(default=20, le=100, description="결과 개수"),
    service: ScreeningService = Depends(get_screening_service)
):
    """
    컵 앤 핸들 패턴 스크리닝 (매집 확인형)

    컵앤핸들 차트 패턴이 형성된 종목을 찾습니다.

    **패턴 조건:**
    - 컵 기간: 60~130일 (3~6개월)
    - 컵 깊이: 좌측 고점 대비 15~40% 하락
    - 우측 고점: 좌측 고점의 90~110%
    - 핸들: 우측 고점 후 5~15% 눌림

    **신호 점수:**
    - 컵 패턴 감지: +25점
    - 핸들 패턴 감지: +15점
    - 돌파 임박 (전고점 -3% 이내): +15점
    - 돌파 확정 (전고점 상회): +25점
    - 거래량 2배 이상: +20점

    **최대 점수:** 100점
    """
    try:
        result = service.run_cup_handle_screening(
            market=market,
            min_score=min_score,
            limit=limit
        )
        return result

    except Exception as e:
        logger.error(f"컵앤핸들 스크리닝 실패: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"스크리닝 중 오류 발생: {str(e)}")


# ============= 기존 엔드포인트 =============


@router.get("/history")
async def get_screening_history(
    start_date: Optional[date] = Query(None, description="시작 날짜"),
    end_date: Optional[date] = Query(None, description="종료 날짜"),
    market: Optional[str] = Query(None, description="시장 (US, KR)"),
    ticker: Optional[str] = Query(None, description="종목 코드"),
    min_score: int = Query(default=50, description="최소 점수"),
    limit: int = Query(default=100, le=500, description="조회 개수"),
    offset: int = Query(default=0, ge=0, description="시작 위치"),
    service: ScreeningService = Depends(get_screening_service)
):
    """
    스크리닝 히스토리 조회

    저장된 스크리닝 결과를 조회합니다.
    """
    try:
        records, total_count = await service.get_screening_history(
            start_date=start_date,
            end_date=end_date,
            market=market,
            ticker=ticker,
            min_score=min_score,
            limit=limit,
            offset=offset
        )

        return {
            "records": records,
            "total_count": total_count,
            "limit": limit,
            "offset": offset
        }

    except Exception as e:
        logger.error(f"스크리닝 히스토리 조회 실패: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"조회 중 오류 발생: {str(e)}")


@router.get("/recommendations")
async def get_recommendations(
    market: Optional[str] = Query(None, description="시장 (US, KR)"),
    limit: int = Query(default=10, le=50, description="결과 개수"),
    service: ScreeningService = Depends(get_screening_service)
):
    """
    최신 추천 종목 조회

    가장 최근 스크리닝 결과에서 추천 종목을 반환합니다.
    """
    try:
        result = await service.get_latest_recommendations(market=market, limit=limit)
        return result

    except Exception as e:
        logger.error(f"추천 종목 조회 실패: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"조회 중 오류 발생: {str(e)}")


@router.get("/criteria")
async def get_screening_criteria():
    """
    스크리닝 기준 정보 조회
    """
    return {
        "trading_value_criteria": {
            "KR": {
                "min_value": 5_000_000_000,
                "description": "5일 평균 거래대금 50억원 이상",
                "unit": "KRW"
            },
            "US": {
                "min_value": 20_000_000,
                "description": "5일 평균 거래대금 $20M 이상",
                "unit": "USD"
            }
        },
        "available_filters": {
            "ichimoku": {
                "description": "일목균형표 분석",
                "max_score": 100,
                "criteria": {
                    "tenkan_period": 9,
                    "kijun_period": 26,
                    "senkou_b_period": 52,
                    "displacement": 26
                }
            },
            "bollinger": {
                "description": "볼린저 밴드 스퀴즈 (에너지 응축형)",
                "max_score": 80,
                "criteria": {
                    "period": 20,
                    "std_dev": 2,
                    "squeeze_percentile": 20,
                    "strong_squeeze_percentile": 10
                }
            },
            "ma_alignment": {
                "description": "이동평균선 정배열 (추세 확정형)",
                "max_score": 95,
                "criteria": {
                    "periods": [5, 20, 60, 120],
                    "disparity_optimal_range": "5~15%"
                }
            },
            "cup_handle": {
                "description": "컵 앤 핸들 패턴 (매집 확인형)",
                "max_score": 100,
                "criteria": {
                    "cup_duration": "60~130일",
                    "cup_depth": "15~40%",
                    "handle_depth": "5~15%"
                }
            }
        },
        "combine_modes": {
            "any": "OR - 선택한 필터 중 하나라도 충족",
            "all": "AND - 선택한 필터 모두 충족"
        },
        "signal_conditions": {
            "perfect_buy": {
                "conditions": [
                    "주가 > 구름대 (선행스팬A, B 모두 위)",
                    "전환선 > 기준선",
                    "후행스팬 > 26일 전 주가"
                ],
                "description": "완벽한 매수 시점 (일목균형표)"
            },
            "strong_buy": {
                "score_range": "80 ~ 100",
                "description": "강한 매수 신호"
            },
            "buy": {
                "score_range": "50 ~ 79",
                "description": "매수 신호"
            },
            "weak_buy": {
                "score_range": "20 ~ 49",
                "description": "약한 매수 신호"
            }
        },
        "ichimoku_score_weights": {
            "price_above_cloud": 30,
            "tenkan_above_kijun": 20,
            "chikou_above_price": 20,
            "cloud_bullish": 10,
            "cloud_breakout_bonus": 15,
            "golden_cross_bonus": 10
        },
        "bollinger_score_weights": {
            "squeeze": 25,
            "strong_squeeze": 35,
            "volume_surge_2x": 20,
            "volume_surge_3x": 30,
            "band_breakout_attempt": 15
        },
        "ma_alignment_score_weights": {
            "perfect_alignment": 40,
            "partial_alignment": 25,
            "golden_cross_5_20": 10,
            "golden_cross_20_60": 15,
            "golden_cross_60_120": 20,
            "disparity_optimal": 10,
            "disparity_overheated": -20
        },
        "cup_handle_score_weights": {
            "cup_detected": 25,
            "handle_detected": 15,
            "breakout_imminent": 15,
            "breakout_confirmed": 25,
            "volume_surge": 20
        },
        "cross_filter_bonus": {
            "description": "여러 필터 동시 충족 시 보너스",
            "two_filters": "+10",
            "three_filters": "+20"
        }
    }
