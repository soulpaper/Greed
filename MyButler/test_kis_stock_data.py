# -*- coding: utf-8 -*-
"""
KIS Stock Data Service 테스트
"""
import logging
import sys

# 로깅 설정
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


def test_kis_service():
    """KIS Stock Data Service 직접 테스트"""
    print("\n" + "=" * 60)
    print("KIS Stock Data Service 테스트")
    print("=" * 60)

    from app.services.kis_stock_data_service import get_kis_stock_data_service

    service = get_kis_stock_data_service()

    # 1. 한국 주식 OHLCV 테스트
    print("\n[1] 한국 주식 OHLCV 테스트 (삼성전자 005930)")
    try:
        df = service.get_kr_ohlcv("005930", period_days=30)
        if df is not None:
            print(f"  - 데이터 건수: {len(df)}")
            print(f"  - 컬럼: {list(df.columns)}")
            print(f"  - 최근 5일:")
            print(df.tail())
        else:
            print("  - 데이터 없음")
    except Exception as e:
        print(f"  - 오류: {e}")

    # 2. 미국 주식 OHLCV 테스트
    print("\n[2] 미국 주식 OHLCV 테스트 (AAPL)")
    try:
        df = service.get_us_ohlcv("AAPL", period_days=30)
        if df is not None:
            print(f"  - 데이터 건수: {len(df)}")
            print(f"  - 컬럼: {list(df.columns)}")
            print(f"  - 최근 5일:")
            print(df.tail())
        else:
            print("  - 데이터 없음")
    except Exception as e:
        print(f"  - 오류: {e}")

    # 3. 한국 시가총액 상위 종목 테스트
    print("\n[3] 한국 시가총액 상위 종목 테스트")
    try:
        stocks = service.get_kr_market_cap_stocks(market="ALL", limit=10)
        print(f"  - 종목 수: {len(stocks)}")
        for s in stocks[:5]:
            print(f"    {s['ticker']}: {s['name']} ({s['market']})")
    except Exception as e:
        print(f"  - 오류: {e}")

    # 4. 미국 거래량 상위 종목 테스트
    print("\n[4] 미국 거래량 상위 종목 테스트 (NASDAQ)")
    try:
        stocks = service.get_us_volume_rank_stocks("NAS", limit=10)
        print(f"  - 종목 수: {len(stocks)}")
        for s in stocks[:5]:
            print(f"    {s['ticker']}: {s['name']} ({s['market']})")
    except Exception as e:
        print(f"  - 오류: {e}")


def test_stock_data_service():
    """Stock Data Service 하이브리드 테스트"""
    print("\n" + "=" * 60)
    print("Stock Data Service 하이브리드 테스트 (KIS 우선)")
    print("=" * 60)

    from app.services.stock_data_service import get_stock_data_service

    service = get_stock_data_service()

    # 1. 한국 주식 OHLCV 테스트
    print("\n[1] 한국 주식 OHLCV 테스트 (삼성전자 005930)")
    try:
        df = service.get_kr_ohlcv("005930")
        if df is not None:
            print(f"  - 데이터 건수: {len(df)}")
            print(f"  - 최근 데이터:")
            print(df.tail(3))
        else:
            print("  - 데이터 없음")
    except Exception as e:
        print(f"  - 오류: {e}")

    # 2. 미국 주식 OHLCV 테스트
    print("\n[2] 미국 주식 OHLCV 테스트 (AAPL)")
    try:
        df = service.get_us_ohlcv("AAPL")
        if df is not None:
            print(f"  - 데이터 건수: {len(df)}")
            print(f"  - 최근 데이터:")
            print(df.tail(3))
        else:
            print("  - 데이터 없음")
    except Exception as e:
        print(f"  - 오류: {e}")

    # 3. 한국 주식 목록 테스트
    print("\n[3] 한국 주식 목록 테스트")
    try:
        stocks = service.get_kr_stock_list(market="KOSPI")
        print(f"  - KOSPI 종목 수: {len(stocks)}")
        if stocks:
            print(f"  - 샘플:")
            for s in stocks[:3]:
                print(f"    {s.get('ticker')}: {s.get('name', 'N/A')}")
    except Exception as e:
        print(f"  - 오류: {e}")

    # 4. 미국 주식 목록 테스트
    print("\n[4] 미국 주식 목록 테스트")
    try:
        stocks = service.get_us_stock_list()
        print(f"  - 종목 수: {len(stocks)}")
        if stocks:
            print(f"  - 샘플:")
            for s in stocks[:3]:
                print(f"    {s.get('ticker')}")
    except Exception as e:
        print(f"  - 오류: {e}")


def test_screening_integration():
    """스크리닝 서비스 통합 테스트"""
    print("\n" + "=" * 60)
    print("스크리닝 서비스 통합 테스트")
    print("=" * 60)

    try:
        from app.services.screening_service import get_screening_service

        screening = get_screening_service()

        print("\n[1] 한국 주식 스크리닝 (limit=5)")
        try:
            result = screening.run_screening(market="KR", limit=5)
            print(f"  - 총 신호: {result.total_signals}")
            if result.signals:
                for sig in result.signals[:3]:
                    print(f"    {sig.ticker}: {sig.signal_type} (강도: {sig.strength})")
        except Exception as e:
            print(f"  - 오류: {e}")

        print("\n[2] 미국 주식 스크리닝 (limit=5)")
        try:
            result = screening.run_screening(market="US", limit=5)
            print(f"  - 총 신호: {result.total_signals}")
            if result.signals:
                for sig in result.signals[:3]:
                    print(f"    {sig.ticker}: {sig.signal_type} (강도: {sig.strength})")
        except Exception as e:
            print(f"  - 오류: {e}")

    except ImportError as e:
        print(f"스크리닝 서비스 import 실패: {e}")


def main():
    print("=" * 60)
    print("KIS Stock Data Service 통합 테스트")
    print("=" * 60)

    # 테스트 선택
    if len(sys.argv) > 1:
        test_type = sys.argv[1]
    else:
        test_type = "all"

    if test_type in ["kis", "all"]:
        test_kis_service()

    if test_type in ["hybrid", "all"]:
        test_stock_data_service()

    if test_type in ["screening", "all"]:
        test_screening_integration()

    print("\n" + "=" * 60)
    print("테스트 완료")
    print("=" * 60)


if __name__ == "__main__":
    main()
