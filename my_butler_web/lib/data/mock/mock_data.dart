import '../models/history_models.dart';
import '../models/screening_models.dart';
import '../models/tag_models.dart';

/// 가데이터 생성 클래스
class MockData {
  MockData._();

  /// 최근 기록 가데이터
  static LatestRecordResponse getLatestRecords() {
    return LatestRecordResponse(
      recordDate: DateTime.now(),
      exchanges: {
        'NASD': {
          'total_eval_amount': 85420000,
          'total_purchase_amount': 72350000,
          'stock_count': 12,
        },
        'NYSE': {
          'total_eval_amount': 42150000,
          'total_purchase_amount': 38900000,
          'stock_count': 8,
        },
        'AMEX': {
          'total_eval_amount': 15680000,
          'total_purchase_amount': 14200000,
          'stock_count': 3,
        },
      },
      totalStocks: 23,
    );
  }

  /// 요약 히스토리 가데이터
  static SummaryHistoryResponse getSummaryHistory() {
    final now = DateTime.now();
    final records = <SummaryRecord>[];

    // 30일치 데이터 생성
    for (var i = 0; i < 30; i++) {
      final date = now.subtract(Duration(days: i));
      final baseEval = 143250000.0 + (30 - i) * 500000 + (i % 3 - 1) * 1200000;
      final basePurchase = 125450000.0;

      records.add(SummaryRecord(
        id: i + 1,
        recordDate: date,
        exchange: 'NASD',
        currency: 'USD',
        totalPurchaseAmount: basePurchase * 0.6,
        totalEvalAmount: baseEval * 0.6,
        totalProfitLoss: (baseEval - basePurchase) * 0.6,
        totalProfitRate: ((baseEval - basePurchase) / basePurchase) * 100,
        stockCount: 12,
        createdAt: date,
      ));

      records.add(SummaryRecord(
        id: i + 100,
        recordDate: date,
        exchange: 'NYSE',
        currency: 'USD',
        totalPurchaseAmount: basePurchase * 0.3,
        totalEvalAmount: baseEval * 0.29,
        totalProfitLoss: (baseEval * 0.29 - basePurchase * 0.3),
        totalProfitRate: ((baseEval * 0.29 - basePurchase * 0.3) / (basePurchase * 0.3)) * 100,
        stockCount: 8,
        createdAt: date,
      ));

      records.add(SummaryRecord(
        id: i + 200,
        recordDate: date,
        exchange: 'AMEX',
        currency: 'USD',
        totalPurchaseAmount: basePurchase * 0.1,
        totalEvalAmount: baseEval * 0.11,
        totalProfitLoss: (baseEval * 0.11 - basePurchase * 0.1),
        totalProfitRate: ((baseEval * 0.11 - basePurchase * 0.1) / (basePurchase * 0.1)) * 100,
        stockCount: 3,
        createdAt: date,
      ));
    }

    return SummaryHistoryResponse(
      records: records,
      totalCount: records.length,
      limit: 100,
      offset: 0,
    );
  }

  /// 종목 히스토리 가데이터
  static StockHistoryResponse getStockHistory() {
    final now = DateTime.now();
    final stocks = [
      {'ticker': 'AAPL', 'name': 'Apple Inc.', 'exchange': 'NASD', 'qty': 50, 'avg': 178.50, 'current': 195.20, 'rate': 9.36},
      {'ticker': 'MSFT', 'name': 'Microsoft Corp.', 'exchange': 'NASD', 'qty': 30, 'avg': 380.00, 'current': 425.80, 'rate': 12.05},
      {'ticker': 'GOOGL', 'name': 'Alphabet Inc.', 'exchange': 'NASD', 'qty': 20, 'avg': 140.25, 'current': 158.90, 'rate': 13.30},
      {'ticker': 'NVDA', 'name': 'NVIDIA Corp.', 'exchange': 'NASD', 'qty': 25, 'avg': 480.00, 'current': 875.50, 'rate': 82.40},
      {'ticker': 'AMZN', 'name': 'Amazon.com Inc.', 'exchange': 'NASD', 'qty': 40, 'avg': 155.80, 'current': 185.40, 'rate': 19.00},
      {'ticker': 'META', 'name': 'Meta Platforms', 'exchange': 'NASD', 'qty': 15, 'avg': 320.00, 'current': 505.60, 'rate': 58.00},
      {'ticker': 'TSLA', 'name': 'Tesla Inc.', 'exchange': 'NASD', 'qty': 35, 'avg': 245.00, 'current': 248.50, 'rate': 1.43},
      {'ticker': 'JPM', 'name': 'JPMorgan Chase', 'exchange': 'NYSE', 'qty': 25, 'avg': 165.50, 'current': 198.30, 'rate': 19.82},
      {'ticker': 'V', 'name': 'Visa Inc.', 'exchange': 'NYSE', 'qty': 20, 'avg': 260.00, 'current': 285.40, 'rate': 9.77},
      {'ticker': 'JNJ', 'name': 'Johnson & Johnson', 'exchange': 'NYSE', 'qty': 30, 'avg': 158.00, 'current': 152.80, 'rate': -3.29},
      {'ticker': 'WMT', 'name': 'Walmart Inc.', 'exchange': 'NYSE', 'qty': 45, 'avg': 162.30, 'current': 175.60, 'rate': 8.19},
      {'ticker': 'PG', 'name': 'Procter & Gamble', 'exchange': 'NYSE', 'qty': 25, 'avg': 155.00, 'current': 168.90, 'rate': 8.97},
    ];

    final records = <StockRecord>[];
    var id = 1;

    for (var day = 0; day < 30; day++) {
      final date = now.subtract(Duration(days: day));
      for (final stock in stocks) {
        final variance = (day % 5 - 2) * 0.5;
        final currentPrice = (stock['current'] as double) * (1 + variance / 100);
        final avgPrice = stock['avg'] as double;
        final qty = (stock['qty'] as int).toDouble();

        records.add(StockRecord(
          id: id++,
          recordDate: date,
          exchange: stock['exchange'] as String,
          currency: 'USD',
          ticker: stock['ticker'] as String,
          stockName: stock['name'] as String,
          quantity: qty,
          avgPurchasePrice: avgPrice,
          currentPrice: currentPrice,
          purchaseAmount: avgPrice * qty,
          evalAmount: currentPrice * qty,
          profitLossAmount: (currentPrice - avgPrice) * qty,
          profitLossRate: ((currentPrice - avgPrice) / avgPrice) * 100,
          createdAt: date,
        ));
      }
    }

    return StockHistoryResponse(
      records: records,
      totalCount: records.length,
      limit: 500,
      offset: 0,
    );
  }

  /// 스크리닝 결과 가데이터 - 전체 종목 데이터
  static final List<StockSignal> _allStockSignals = [
    // 강력 매수
    StockSignal(
      ticker: 'NVDA',
      name: 'NVIDIA Corporation',
      market: 'US',
      currentPrice: 875.50,
      signalStrength: 'STRONG_BUY',
      score: 92,
      priceAboveCloud: true,
      tenkanAboveKijun: true,
      chikouAbovePrice: true,
      cloudBullish: true,
      bollingerSqueeze: true,
      bollingerScore: 85,
      maPerfectAlignment: true,
      maAlignmentScore: 90,
      totalTechnicalScore: 92,
      totalFundamentalScore: 78,
      activePatterns: ['일목균형표', '볼린저스퀴즈', '이평선정배열'],
    ),
    StockSignal(
      ticker: 'META',
      name: 'Meta Platforms Inc.',
      market: 'US',
      currentPrice: 505.60,
      signalStrength: 'STRONG_BUY',
      score: 88,
      priceAboveCloud: true,
      tenkanAboveKijun: true,
      cloudBullish: true,
      maPerfectAlignment: true,
      maAlignmentScore: 85,
      roeScore: 80,
      roeValue: 28.5,
      totalTechnicalScore: 88,
      totalFundamentalScore: 82,
      activePatterns: ['일목균형표', '이평선정배열'],
      fundamentalPatterns: ['고ROE'],
    ),
    // 매수
    StockSignal(
      ticker: 'AAPL',
      name: 'Apple Inc.',
      market: 'US',
      currentPrice: 195.20,
      signalStrength: 'BUY',
      score: 75,
      priceAboveCloud: true,
      tenkanAboveKijun: true,
      bollingerScore: 70,
      totalTechnicalScore: 75,
      totalFundamentalScore: 85,
      activePatterns: ['일목균형표'],
      fundamentalPatterns: ['고ROE', '저부채'],
    ),
    StockSignal(
      ticker: 'MSFT',
      name: 'Microsoft Corporation',
      market: 'US',
      currentPrice: 425.80,
      signalStrength: 'BUY',
      score: 72,
      priceAboveCloud: true,
      cloudBullish: true,
      maPerfectAlignment: true,
      maAlignmentScore: 65,
      roeScore: 75,
      roeValue: 35.2,
      totalTechnicalScore: 72,
      totalFundamentalScore: 88,
      activePatterns: ['일목균형표', '이평선정배열'],
      fundamentalPatterns: ['고ROE', '고GPM'],
    ),
    StockSignal(
      ticker: 'GOOGL',
      name: 'Alphabet Inc.',
      market: 'US',
      currentPrice: 158.90,
      signalStrength: 'BUY',
      score: 68,
      priceAboveCloud: true,
      tenkanAboveKijun: true,
      cupHandlePattern: true,
      cupHandleScore: 72,
      totalTechnicalScore: 68,
      totalFundamentalScore: 75,
      activePatterns: ['일목균형표', '컵앤핸들'],
    ),
    // 약매수
    StockSignal(
      ticker: 'AMZN',
      name: 'Amazon.com Inc.',
      market: 'US',
      currentPrice: 185.40,
      signalStrength: 'WEAK_BUY',
      score: 58,
      priceAboveCloud: true,
      cupHandlePattern: true,
      cupHandleScore: 65,
      cupHandleBreakoutImminent: true,
      totalTechnicalScore: 58,
      totalFundamentalScore: 62,
      activePatterns: ['일목균형표', '컵앤핸들'],
    ),
    StockSignal(
      ticker: 'TSLA',
      name: 'Tesla Inc.',
      market: 'US',
      currentPrice: 248.50,
      signalStrength: 'WEAK_BUY',
      score: 52,
      bollingerSqueeze: true,
      bollingerScore: 55,
      totalTechnicalScore: 52,
      totalFundamentalScore: 45,
      activePatterns: ['볼린저스퀴즈'],
    ),
    StockSignal(
      ticker: 'AMD',
      name: 'Advanced Micro Devices',
      market: 'US',
      currentPrice: 178.30,
      signalStrength: 'WEAK_BUY',
      score: 55,
      bollingerSqueeze: true,
      bollingerScore: 60,
      maPerfectAlignment: true,
      maAlignmentScore: 58,
      totalTechnicalScore: 55,
      totalFundamentalScore: 52,
      activePatterns: ['볼린저스퀴즈', '이평선정배열'],
    ),
    StockSignal(
      ticker: 'CRM',
      name: 'Salesforce Inc.',
      market: 'US',
      currentPrice: 285.40,
      signalStrength: 'BUY',
      score: 70,
      maPerfectAlignment: true,
      maAlignmentScore: 78,
      cupHandlePattern: true,
      cupHandleScore: 68,
      totalTechnicalScore: 70,
      totalFundamentalScore: 65,
      activePatterns: ['이평선정배열', '컵앤핸들'],
    ),
    StockSignal(
      ticker: 'NFLX',
      name: 'Netflix Inc.',
      market: 'US',
      currentPrice: 625.80,
      signalStrength: 'BUY',
      score: 74,
      bollingerSqueeze: true,
      bollingerScore: 72,
      priceAboveCloud: true,
      tenkanAboveKijun: true,
      totalTechnicalScore: 74,
      totalFundamentalScore: 68,
      activePatterns: ['볼린저스퀴즈', '일목균형표'],
    ),
  ];

  /// 종합 스크리닝 결과 (모든 신호)
  static ScreeningResponse getScreeningResult() {
    return _buildScreeningResponse(_allStockSignals);
  }

  /// 일목균형표 조건 충족 종목
  static ScreeningResponse getIchimokuScreeningResult() {
    final filtered = _allStockSignals.where((s) =>
      s.priceAboveCloud || s.tenkanAboveKijun || s.cloudBullish
    ).toList();
    return _buildScreeningResponse(filtered);
  }

  /// 볼린저밴드 스퀴즈 종목
  static ScreeningResponse getBollingerScreeningResult() {
    final filtered = _allStockSignals.where((s) =>
      s.bollingerSqueeze || s.bollingerScore > 50
    ).toList();
    return _buildScreeningResponse(filtered);
  }

  /// 이평선 정배열 종목
  static ScreeningResponse getMAAlignmentScreeningResult() {
    final filtered = _allStockSignals.where((s) =>
      s.maPerfectAlignment || s.maAlignmentScore > 50
    ).toList();
    return _buildScreeningResponse(filtered);
  }

  /// 컵앤핸들 패턴 종목
  static ScreeningResponse getCupHandleScreeningResult() {
    final filtered = _allStockSignals.where((s) =>
      s.cupHandlePattern || s.cupHandleScore > 50
    ).toList();
    return _buildScreeningResponse(filtered);
  }

  /// ScreeningResponse 빌더 헬퍼
  static ScreeningResponse _buildScreeningResponse(List<StockSignal> signals) {
    final strongBuy = signals.where((s) => s.signalStrength == 'STRONG_BUY').toList();
    final buy = signals.where((s) => s.signalStrength == 'BUY').toList();
    final weakBuy = signals.where((s) => s.signalStrength == 'WEAK_BUY').toList();

    return ScreeningResponse(
      screeningDate: DateTime.now(),
      market: 'ALL',
      totalScanned: 2500,
      totalPassedFilter: signals.length + 20,
      totalSignals: signals.length,
      strongBuy: strongBuy,
      buy: buy,
      weakBuy: weakBuy,
      summary: {
        'strong_buy_count': strongBuy.length,
        'buy_count': buy.length,
        'weak_buy_count': weakBuy.length,
      },
    );
  }

  /// 추천 종목 가데이터
  static DailyRecommendation getRecommendations() {
    return DailyRecommendation(
      date: DateTime.now(),
      usRecommendations: [
        StockSignal(
          ticker: 'NVDA',
          name: 'NVIDIA Corporation',
          market: 'US',
          currentPrice: 875.50,
          signalStrength: 'STRONG_BUY',
          score: 92,
          totalTechnicalScore: 92,
          activePatterns: ['일목균형표', '볼린저스퀴즈'],
        ),
        StockSignal(
          ticker: 'META',
          name: 'Meta Platforms Inc.',
          market: 'US',
          currentPrice: 505.60,
          signalStrength: 'STRONG_BUY',
          score: 88,
          totalTechnicalScore: 88,
          activePatterns: ['일목균형표', '이평선정배열'],
        ),
        StockSignal(
          ticker: 'AAPL',
          name: 'Apple Inc.',
          market: 'US',
          currentPrice: 195.20,
          signalStrength: 'BUY',
          score: 75,
          totalTechnicalScore: 75,
          activePatterns: ['일목균형표'],
        ),
      ],
      krRecommendations: [
        StockSignal(
          ticker: '005930',
          name: '삼성전자',
          market: 'KR',
          currentPrice: 72500,
          signalStrength: 'BUY',
          score: 70,
          totalTechnicalScore: 70,
          activePatterns: ['일목균형표'],
        ),
        StockSignal(
          ticker: '000660',
          name: 'SK하이닉스',
          market: 'KR',
          currentPrice: 185000,
          signalStrength: 'WEAK_BUY',
          score: 58,
          totalTechnicalScore: 58,
          activePatterns: ['볼린저스퀴즈'],
        ),
      ],
      totalCount: 5,
      generatedAt: DateTime.now(),
    );
  }

  /// 태그 목록 가데이터
  static TagListResponse getTags() {
    return TagListResponse(
      tags: [
        AssetTag(
          id: 1,
          name: '핵심 보유',
          category: '전략',
          color: '#3FB950',
          description: '장기 보유 핵심 종목',
          createdAt: DateTime.now().subtract(const Duration(days: 30)),
        ),
        AssetTag(
          id: 2,
          name: '성장주',
          category: '전략',
          color: '#58A6FF',
          description: '고성장 기대 종목',
          createdAt: DateTime.now().subtract(const Duration(days: 25)),
        ),
        AssetTag(
          id: 3,
          name: '배당주',
          category: '전략',
          color: '#D29922',
          description: '배당 수익 목적',
          createdAt: DateTime.now().subtract(const Duration(days: 20)),
        ),
        AssetTag(
          id: 4,
          name: 'IT/반도체',
          category: '섹터',
          color: '#A371F7',
          description: 'IT 및 반도체 관련',
          createdAt: DateTime.now().subtract(const Duration(days: 15)),
        ),
        AssetTag(
          id: 5,
          name: '금융',
          category: '섹터',
          color: '#F85149',
          description: '금융 섹터',
          createdAt: DateTime.now().subtract(const Duration(days: 10)),
        ),
        AssetTag(
          id: 6,
          name: '소비재',
          category: '섹터',
          color: '#79C0FF',
          description: '소비재 섹터',
          createdAt: DateTime.now().subtract(const Duration(days: 5)),
        ),
      ],
      totalCount: 6,
    );
  }

  /// 태그별 종목 가데이터
  static StocksByTagResponse getStocksByTag(int tagId) {
    final tags = getTags().tags;
    final tag = tags.firstWhere((t) => t.id == tagId, orElse: () => tags.first);

    final stocksByTag = <int, List<StockWithTags>>{
      1: [
        StockWithTags(ticker: 'AAPL', stockName: 'Apple Inc.', exchange: 'NASD', tags: [tag]),
        StockWithTags(ticker: 'MSFT', stockName: 'Microsoft Corp.', exchange: 'NASD', tags: [tag]),
        StockWithTags(ticker: 'GOOGL', stockName: 'Alphabet Inc.', exchange: 'NASD', tags: [tag]),
      ],
      2: [
        StockWithTags(ticker: 'NVDA', stockName: 'NVIDIA Corp.', exchange: 'NASD', tags: [tag]),
        StockWithTags(ticker: 'META', stockName: 'Meta Platforms', exchange: 'NASD', tags: [tag]),
        StockWithTags(ticker: 'TSLA', stockName: 'Tesla Inc.', exchange: 'NASD', tags: [tag]),
      ],
      3: [
        StockWithTags(ticker: 'JNJ', stockName: 'Johnson & Johnson', exchange: 'NYSE', tags: [tag]),
        StockWithTags(ticker: 'PG', stockName: 'Procter & Gamble', exchange: 'NYSE', tags: [tag]),
      ],
      4: [
        StockWithTags(ticker: 'NVDA', stockName: 'NVIDIA Corp.', exchange: 'NASD', tags: [tag]),
        StockWithTags(ticker: 'AAPL', stockName: 'Apple Inc.', exchange: 'NASD', tags: [tag]),
        StockWithTags(ticker: 'MSFT', stockName: 'Microsoft Corp.', exchange: 'NASD', tags: [tag]),
      ],
      5: [
        StockWithTags(ticker: 'JPM', stockName: 'JPMorgan Chase', exchange: 'NYSE', tags: [tag]),
        StockWithTags(ticker: 'V', stockName: 'Visa Inc.', exchange: 'NYSE', tags: [tag]),
      ],
      6: [
        StockWithTags(ticker: 'AMZN', stockName: 'Amazon.com Inc.', exchange: 'NASD', tags: [tag]),
        StockWithTags(ticker: 'WMT', stockName: 'Walmart Inc.', exchange: 'NYSE', tags: [tag]),
      ],
    };

    final stocks = stocksByTag[tagId] ?? [];

    return StocksByTagResponse(
      tag: tag,
      stocks: stocks,
      totalCount: stocks.length,
    );
  }
}
