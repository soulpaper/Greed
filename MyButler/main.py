# -*- coding: utf-8 -*-
"""
MyButler - 주식 포트폴리오 기록 및 스크리닝 시스템
FastAPI 메인 애플리케이션
"""
import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.config.database_config import init_sqlite_schema, close_redis_connection
from app.controllers.history_controller import router as history_router
from app.controllers.screening_controller import router as screening_router
from app.controllers.tag_controller import router as tag_router
from app.scheduler.scheduler_manager import get_scheduler_manager

# 로깅 설정
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """애플리케이션 라이프사이클 관리"""
    # 시작 시
    logger.info("애플리케이션 시작...")

    # DB 스키마 초기화
    init_sqlite_schema()
    logger.info("데이터베이스 스키마 초기화 완료")

    # 스케줄러 시작
    scheduler = get_scheduler_manager()
    scheduler.start()
    logger.info("스케줄러 시작 완료")

    yield

    # 종료 시
    logger.info("애플리케이션 종료...")

    # 스케줄러 종료
    scheduler.shutdown()
    logger.info("스케줄러 종료 완료")

    # Redis 연결 종료
    await close_redis_connection()
    logger.info("Redis 연결 종료 완료")


# FastAPI 앱 생성
app = FastAPI(
    title="MyButler API",
    description="주식 포트폴리오 기록 및 스크리닝 시스템",
    version="1.0.0",
    lifespan=lifespan
)

# CORS 설정
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 라우터 등록
app.include_router(history_router)
app.include_router(screening_router)
app.include_router(tag_router)


@app.get("/")
async def root():
    """API 루트 엔드포인트"""
    return {
        "name": "MyButler API",
        "version": "1.0.0",
        "description": "주식 포트폴리오 기록 및 스크리닝 시스템"
    }


@app.get("/health")
async def health_check():
    """헬스 체크 엔드포인트"""
    return {"status": "healthy"}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)
