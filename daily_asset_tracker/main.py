from fastapi import FastAPI, BackgroundTasks
from contextlib import asynccontextmanager
from daily_asset_tracker.scheduler import start_scheduler, shutdown_scheduler
from daily_asset_tracker.database import engine, Base
from daily_asset_tracker.service import fetch_and_save_account_status
import logging

# 로깅 설정
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# DB 테이블 생성
Base.metadata.create_all(bind=engine)

@asynccontextmanager
async def lifespan(app: FastAPI):
    # 앱 시작 시 스케줄러 시작
    start_scheduler()
    yield
    # 앱 종료 시 스케줄러 종료
    shutdown_scheduler()

app = FastAPI(title="Daily Asset Tracker", lifespan=lifespan)

@app.get("/")
def read_root():
    return {"message": "Daily Asset Tracker Service is running."}

@app.post("/manual-fetch")
def trigger_manual_fetch(background_tasks: BackgroundTasks):
    """
    수동으로 계좌 상태 확인 및 저장을 트리거합니다. (테스트용)
    """
    background_tasks.add_task(fetch_and_save_account_status)
    return {"message": "Manual fetch triggered in background."}
