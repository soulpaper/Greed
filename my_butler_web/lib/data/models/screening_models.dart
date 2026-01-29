/// Screening API 데이터 모델
library;

enum MarketType { US, KR, ALL }

enum SignalStrength {
  strongBuy,
  buy,
  weakBuy,
  neutral,
  weakSell,
  sell,
  strongSell;

  static SignalStrength fromString(String value) {
    switch (value.toUpperCase()) {
      case 'STRONG_BUY':
        return SignalStrength.strongBuy;
      case 'BUY':
        return SignalStrength.buy;
      case 'WEAK_BUY':
        return SignalStrength.weakBuy;
      case 'NEUTRAL':
        return SignalStrength.neutral;
      case 'WEAK_SELL':
        return SignalStrength.weakSell;
      case 'SELL':
        return SignalStrength.sell;
      case 'STRONG_SELL':
        return SignalStrength.strongSell;
      default:
        return SignalStrength.neutral;
    }
  }

  String get displayName {
    switch (this) {
      case SignalStrength.strongBuy:
        return '강력 매수';
      case SignalStrength.buy:
        return '매수';
      case SignalStrength.weakBuy:
        return '약매수';
      case SignalStrength.neutral:
        return '중립';
      case SignalStrength.weakSell:
        return '약매도';
      case SignalStrength.sell:
        return '매도';
      case SignalStrength.strongSell:
        return '강력 매도';
    }
  }
}

enum FilterType {
  ichimoku('ichimoku', '일목균형표'),
  bollinger('bollinger', '볼린저밴드'),
  maAlignment('ma_alignment', '이평선정배열'),
  cupHandle('cup_handle', '컵앤핸들'),
  roe('roe', 'ROE'),
  gpm('gpm', 'GPM'),
  debt('debt', '부채비율'),
  capex('capex', 'CapEx');

  const FilterType(this.value, this.displayName);
  final String value;
  final String displayName;
}

enum CombineMode {
  any('any', 'OR'),
  all('all', 'AND');

  const CombineMode(this.value, this.displayName);
  final String value;
  final String displayName;
}

class StockSignal {
  final String ticker;
  final String name;
  final String market;
  final double currentPrice;
  final String signalStrength;
  final int score;

  // 일목균형표
  final bool priceAboveCloud;
  final bool tenkanAboveKijun;
  final bool chikouAbovePrice;
  final bool cloudBullish;
  final bool cloudBreakout;
  final bool goldenCross;
  final bool thinCloud;

  // 볼린저밴드
  final bool bollingerSqueeze;
  final int bollingerScore;
  final double? bollingerBandwidth;
  final double? bollingerPercentB;

  // 이동평균 정배열
  final bool maPerfectAlignment;
  final int maAlignmentScore;
  final double? maDisparity;

  // 컵앤핸들
  final bool cupHandlePattern;
  final int cupHandleScore;
  final bool cupHandleBreakoutImminent;

  // 펀더멘탈
  final int roeScore;
  final double? roeValue;
  final int gpmScore;
  final double? gpmValue;
  final int debtScore;
  final double? debtRatio;
  final int capexScore;
  final double? capexRatio;

  // 종합
  final int totalTechnicalScore;
  final int totalFundamentalScore;
  final List<String> activePatterns;
  final List<String> fundamentalPatterns;

  StockSignal({
    required this.ticker,
    required this.name,
    required this.market,
    required this.currentPrice,
    required this.signalStrength,
    required this.score,
    this.priceAboveCloud = false,
    this.tenkanAboveKijun = false,
    this.chikouAbovePrice = false,
    this.cloudBullish = false,
    this.cloudBreakout = false,
    this.goldenCross = false,
    this.thinCloud = false,
    this.bollingerSqueeze = false,
    this.bollingerScore = 0,
    this.bollingerBandwidth,
    this.bollingerPercentB,
    this.maPerfectAlignment = false,
    this.maAlignmentScore = 0,
    this.maDisparity,
    this.cupHandlePattern = false,
    this.cupHandleScore = 0,
    this.cupHandleBreakoutImminent = false,
    this.roeScore = 0,
    this.roeValue,
    this.gpmScore = 0,
    this.gpmValue,
    this.debtScore = 0,
    this.debtRatio,
    this.capexScore = 0,
    this.capexRatio,
    this.totalTechnicalScore = 0,
    this.totalFundamentalScore = 0,
    this.activePatterns = const [],
    this.fundamentalPatterns = const [],
  });

  SignalStrength get signalType => SignalStrength.fromString(signalStrength);

  factory StockSignal.fromJson(Map<String, dynamic> json) {
    return StockSignal(
      ticker: json['ticker'],
      name: json['name'],
      market: json['market'],
      currentPrice: json['current_price'].toDouble(),
      signalStrength: json['signal_strength'],
      score: json['score'],
      priceAboveCloud: json['price_above_cloud'] ?? false,
      tenkanAboveKijun: json['tenkan_above_kijun'] ?? false,
      chikouAbovePrice: json['chikou_above_price'] ?? false,
      cloudBullish: json['cloud_bullish'] ?? false,
      cloudBreakout: json['cloud_breakout'] ?? false,
      goldenCross: json['golden_cross'] ?? false,
      thinCloud: json['thin_cloud'] ?? false,
      bollingerSqueeze: json['bollinger_squeeze'] ?? false,
      bollingerScore: json['bollinger_score'] ?? 0,
      bollingerBandwidth: json['bollinger_bandwidth']?.toDouble(),
      bollingerPercentB: json['bollinger_percent_b']?.toDouble(),
      maPerfectAlignment: json['ma_perfect_alignment'] ?? false,
      maAlignmentScore: json['ma_alignment_score'] ?? 0,
      maDisparity: json['ma_disparity']?.toDouble(),
      cupHandlePattern: json['cup_handle_pattern'] ?? false,
      cupHandleScore: json['cup_handle_score'] ?? 0,
      cupHandleBreakoutImminent: json['cup_handle_breakout_imminent'] ?? false,
      roeScore: json['roe_score'] ?? 0,
      roeValue: json['roe_value']?.toDouble(),
      gpmScore: json['gpm_score'] ?? 0,
      gpmValue: json['gpm_value']?.toDouble(),
      debtScore: json['debt_score'] ?? 0,
      debtRatio: json['debt_ratio']?.toDouble(),
      capexScore: json['capex_score'] ?? 0,
      capexRatio: json['capex_ratio']?.toDouble(),
      totalTechnicalScore: json['total_technical_score'] ?? 0,
      totalFundamentalScore: json['total_fundamental_score'] ?? 0,
      activePatterns: List<String>.from(json['active_patterns'] ?? []),
      fundamentalPatterns: List<String>.from(
        json['fundamental_patterns'] ?? [],
      ),
    );
  }
}

class ScreeningResponse {
  final DateTime screeningDate;
  final String market;
  final int totalScanned;
  final int totalPassedFilter;
  final int totalSignals;
  final List<StockSignal> strongBuy;
  final List<StockSignal> buy;
  final List<StockSignal> weakBuy;
  final Map<String, dynamic> summary;

  ScreeningResponse({
    required this.screeningDate,
    required this.market,
    required this.totalScanned,
    required this.totalPassedFilter,
    required this.totalSignals,
    required this.strongBuy,
    required this.buy,
    required this.weakBuy,
    required this.summary,
  });

  List<StockSignal> get allSignals => [...strongBuy, ...buy, ...weakBuy];

  factory ScreeningResponse.fromJson(Map<String, dynamic> json) {
    return ScreeningResponse(
      screeningDate: DateTime.parse(json['screening_date']),
      market: json['market'],
      totalScanned: json['total_scanned'],
      totalPassedFilter: json['total_passed_filter'],
      totalSignals: json['total_signals'],
      strongBuy: (json['strong_buy'] as List)
          .map((e) => StockSignal.fromJson(e))
          .toList(),
      buy: (json['buy'] as List).map((e) => StockSignal.fromJson(e)).toList(),
      weakBuy: (json['weak_buy'] as List)
          .map((e) => StockSignal.fromJson(e))
          .toList(),
      summary: json['summary'] ?? {},
    );
  }
}

class DailyRecommendation {
  final DateTime date;
  final List<StockSignal> usRecommendations;
  final List<StockSignal> krRecommendations;
  final int totalCount;
  final DateTime generatedAt;

  DailyRecommendation({
    required this.date,
    required this.usRecommendations,
    required this.krRecommendations,
    required this.totalCount,
    required this.generatedAt,
  });

  factory DailyRecommendation.fromJson(Map<String, dynamic> json) {
    return DailyRecommendation(
      date: DateTime.parse(json['date']),
      usRecommendations: (json['us_recommendations'] as List)
          .map((e) => StockSignal.fromJson(e))
          .toList(),
      krRecommendations: (json['kr_recommendations'] as List)
          .map((e) => StockSignal.fromJson(e))
          .toList(),
      totalCount: json['total_count'],
      generatedAt: DateTime.parse(json['generated_at']),
    );
  }
}

class ScreeningRequest {
  final String market;
  final int minScore;
  final bool perfectOnly;
  final int limit;
  final List<String> filters;
  final String combineMode;

  ScreeningRequest({
    this.market = 'ALL',
    this.minScore = 50,
    this.perfectOnly = false,
    this.limit = 20,
    this.filters = const ['ichimoku'],
    this.combineMode = 'any',
  });

  Map<String, dynamic> toJson() {
    return {
      'market': market,
      'min_score': minScore,
      'perfect_only': perfectOnly,
      'limit': limit,
      'filters': filters,
      'combine_mode': combineMode,
    };
  }
}
