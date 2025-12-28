from sqlalchemy import Column, Integer, String, Float, DateTime, ForeignKey, Numeric
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from daily_asset_tracker.database import Base

class AccountSnapshot(Base):
    __tablename__ = "account_snapshots"

    id = Column(Integer, primary_key=True, index=True)
    snapshot_date = Column(DateTime(timezone=True), default=func.now(), index=True)

    total_asset_amount = Column(Numeric(18, 2), comment="총 평가 자산 금액")
    total_deposit = Column(Numeric(18, 2), comment="예수금")
    total_purchase_amount = Column(Numeric(18, 2), comment="총 매입 금액")
    total_evaluation_profit = Column(Numeric(18, 2), comment="총 평가 손익")

    holdings = relationship("StockHolding", back_populates="snapshot")

class StockHolding(Base):
    __tablename__ = "stock_holdings"

    id = Column(Integer, primary_key=True, index=True)
    snapshot_id = Column(Integer, ForeignKey("account_snapshots.id"))

    pdno = Column(String, comment="종목코드")
    prdt_name = Column(String, comment="종목명")

    hldg_qty = Column(Integer, comment="보유수량")
    pchs_avg_pric = Column(Numeric(18, 2), comment="매입평균가격")
    prpr = Column(Numeric(18, 2), comment="현재가")
    evlu_amt = Column(Numeric(18, 2), comment="평가금액")
    evlu_pfls_amt = Column(Numeric(18, 2), comment="평가손익금액")
    evlu_pfls_rt = Column(Float, comment="평가손익율")

    snapshot = relationship("AccountSnapshot", back_populates="holdings")
