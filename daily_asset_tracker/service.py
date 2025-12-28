import logging
from datetime import datetime
from sqlalchemy.orm import Session
from daily_asset_tracker.database import SessionLocal
from daily_asset_tracker.models import AccountSnapshot, StockHolding
from daily_asset_tracker.kis_api import kis_client

logger = logging.getLogger(__name__)

def fetch_and_save_account_status():
    """
    KIS API를 통해 계좌 잔고를 조회하고 DB에 저장합니다.
    """
    logger.info("Starting account status fetch...")
    db: Session = SessionLocal()
    try:
        # API 호출
        data = kis_client.inquire_balance()

        output1 = data.get('output1', []) # 보유종목 리스트
        output2 = data.get('output2', []) # 계좌평가현황 (리스트 형태일 수 있음)

        if not output2:
            logger.error("No account summary data (output2) received.")
            return

        # output2가 리스트라면 첫 번째 요소 사용
        summary = output2[0] if isinstance(output2, list) else output2

        # AccountSnapshot 생성
        snapshot = AccountSnapshot(
            snapshot_date=datetime.now(),
            total_asset_amount=float(summary.get('tot_evlu_amt', 0)),
            total_deposit=float(summary.get('dnca_tot_amt', 0)),
            total_purchase_amount=float(summary.get('pchs_amt_smtl_amt', 0)),
            total_evaluation_profit=float(summary.get('evlu_pfls_smtl_amt', 0))
        )

        db.add(snapshot)
        db.flush() # ID 생성을 위해 flush

        # StockHolding 생성
        for item in output1:
            holding = StockHolding(
                snapshot_id=snapshot.id,
                pdno=item.get('pdno'),
                prdt_name=item.get('prdt_name'),
                hldg_qty=int(item.get('hldg_qty', 0)),
                pchs_avg_pric=float(item.get('pchs_avg_pric', 0)),
                prpr=float(item.get('prpr', 0)),
                evlu_amt=float(item.get('evlu_amt', 0)),
                evlu_pfls_amt=float(item.get('evlu_pfls_amt', 0)),
                evlu_pfls_rt=float(item.get('evlu_pfls_rt', 0))
            )
            db.add(holding)

        db.commit()
        logger.info(f"Successfully saved account snapshot {snapshot.id} with {len(output1)} holdings.")

    except Exception as e:
        logger.error(f"Error in fetch_and_save_account_status: {e}")
        db.rollback()
    finally:
        db.close()
