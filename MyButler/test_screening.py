# -*- coding: utf-8 -*-
"""
Screening Test
"""
import sys
import os
import logging

# Windows 콘솔 인코딩 설정
if sys.platform == 'win32':
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def test_us_screening():
    """US Stock Screening Test"""
    print("\n" + "="*60)
    print("[US] Stock Screening Test")
    print("="*60)

    from app.services.screening_service import get_screening_service
    from app.models.screening_models import MarketType

    service = get_screening_service()

    result = service.run_screening(
        market=MarketType.US,
        min_score=50,
        perfect_only=False,
        limit=10
    )

    print(f"\n[Summary]")
    print(f"  - Total scanned: {result.total_scanned}")
    print(f"  - Passed trading value filter: {result.total_passed_filter}")
    print(f"  - Total signals: {result.total_signals}")

    print(f"\n[STRONG_BUY] ({len(result.strong_buy)})")
    for s in result.strong_buy[:5]:
        print(f"  {s.ticker:8} | Score: {s.score:3} | Price: ${s.current_price:,.2f}")
        print(f"           | Cloud+:{s.price_above_cloud} TK>KJ:{s.tenkan_above_kijun} Chikou+:{s.chikou_above_price}")

    print(f"\n[BUY] ({len(result.buy)})")
    for s in result.buy[:5]:
        print(f"  {s.ticker:8} | Score: {s.score:3} | Price: ${s.current_price:,.2f}")
        print(f"           | Cloud+:{s.price_above_cloud} TK>KJ:{s.tenkan_above_kijun} Chikou+:{s.chikou_above_price}")

    print(f"\n[WEAK_BUY] ({len(result.weak_buy)})")
    for s in result.weak_buy[:3]:
        print(f"  {s.ticker:8} | Score: {s.score:3} | Price: ${s.current_price:,.2f}")

    return result


def test_kr_screening():
    """Korean Stock Screening Test"""
    print("\n" + "="*60)
    print("[KR] Stock Screening Test")
    print("="*60)

    from app.services.screening_service import get_screening_service
    from app.models.screening_models import MarketType

    service = get_screening_service()

    result = service.run_screening(
        market=MarketType.KR,
        min_score=50,
        perfect_only=False,
        limit=10
    )

    print(f"\n[Summary]")
    print(f"  - Total scanned: {result.total_scanned}")
    print(f"  - Passed trading value filter: {result.total_passed_filter}")
    print(f"  - Total signals: {result.total_signals}")

    print(f"\n[STRONG_BUY] ({len(result.strong_buy)})")
    for s in result.strong_buy[:5]:
        print(f"  {s.ticker:8} {s.name[:12]:12} | Score: {s.score:3} | Price: {s.current_price:,.0f}")

    print(f"\n[BUY] ({len(result.buy)})")
    for s in result.buy[:5]:
        print(f"  {s.ticker:8} {s.name[:12]:12} | Score: {s.score:3} | Price: {s.current_price:,.0f}")

    return result


def test_perfect_signals():
    """Perfect Condition Test"""
    print("\n" + "="*60)
    print("[PERFECT] Price>Cloud + Tenkan>Kijun + Chikou>Price26")
    print("="*60)

    from app.services.screening_service import get_screening_service
    from app.models.screening_models import MarketType

    service = get_screening_service()

    result = service.run_screening(
        market=MarketType.US,
        min_score=0,
        perfect_only=True,
        limit=20
    )

    all_perfect = result.strong_buy + result.buy + result.weak_buy

    print(f"\nPerfect condition stocks: {len(all_perfect)}")
    for s in all_perfect[:10]:
        extras = []
        if s.cloud_breakout:
            extras.append("CloudBreakout")
        if s.golden_cross:
            extras.append("GoldenCross")
        extra_str = f" | Bonus: {', '.join(extras)}" if extras else ""
        print(f"  {s.ticker:8} | Score: {s.score:3} | ${s.current_price:,.2f}{extra_str}")

    return result


def test_single_stock():
    """Single Stock Analysis (AAPL)"""
    print("\n" + "="*60)
    print("[SINGLE] AAPL Ichimoku Analysis")
    print("="*60)

    from app.services.stock_data_service import get_stock_data_service
    from app.services.ichimoku_service import get_ichimoku_service

    stock_service = get_stock_data_service()
    ichimoku_service = get_ichimoku_service()

    df = stock_service.get_us_ohlcv("AAPL", period_days=100)

    if df is not None:
        print(f"\nData period: {df.index[0].date()} ~ {df.index[-1].date()}")
        print(f"Data count: {len(df)} days")

        signal = ichimoku_service.analyze_signal(df, "AAPL", name="Apple Inc.", market="US")

        if signal:
            print(f"\n[AAPL Analysis Result]")
            print(f"  Current Price: ${signal.current_price:,.2f}")
            print(f"  Signal: {signal.signal_strength.value}")
            print(f"  Score: {signal.score}")
            print(f"\n  [Ichimoku Values]")
            print(f"    Tenkan-sen:    ${signal.tenkan_sen:,.2f}")
            print(f"    Kijun-sen:     ${signal.kijun_sen:,.2f}")
            print(f"    Senkou Span A: ${signal.senkou_span_a:,.2f}")
            print(f"    Senkou Span B: ${signal.senkou_span_b:,.2f}")
            print(f"\n  [Conditions]")
            print(f"    Price > Cloud:     {signal.price_above_cloud}")
            print(f"    Tenkan > Kijun:    {signal.tenkan_above_kijun}")
            print(f"    Chikou > Price26:  {signal.chikou_above_price}")
            print(f"    Bullish Cloud:     {signal.cloud_bullish}")
            print(f"    Cloud Breakout:    {signal.cloud_breakout}")
            print(f"    Golden Cross:      {signal.golden_cross}")
    else:
        print("Failed to fetch data.")


if __name__ == "__main__":
    print("="*60)
    print("Ichimoku Screening Test")
    print("="*60)

    test_type = sys.argv[1] if len(sys.argv) > 1 else "us"

    try:
        if test_type == "single":
            test_single_stock()
        elif test_type == "us":
            test_us_screening()
        elif test_type == "kr":
            test_kr_screening()
        elif test_type == "perfect":
            test_perfect_signals()
        elif test_type == "all":
            test_single_stock()
            test_us_screening()
            test_perfect_signals()
        else:
            print(f"Unknown test: {test_type}")
            print("Usage: python test_screening.py [single|us|kr|perfect|all]")
    except Exception as e:
        logger.error(f"Test failed: {e}", exc_info=True)
